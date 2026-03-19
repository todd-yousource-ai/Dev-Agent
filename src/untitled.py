// App/Composition/ServiceKey.swift
// Forge Platform — Dependency Injection Core
// Type-erased hashable key for identifying service registrations by metatype and optional qualifier.
//
// Security assumptions:
// - ServiceKey is Sendable and immutable; safe for concurrent access across actors.
// - typeName is stored for diagnostics only; never used in equality/hashing (avoids spoofing via name collision).
// - ObjectIdentifier provides compiler-guaranteed uniqueness per Swift metatype.
// - No heap allocation beyond stored strings. Qualifier and typeName are value-typed (Copy-on-Write).

import Foundation

/// A type-erased, hashable key that uniquely identifies a service registration
/// by its Swift metatype and an optional qualifier string.
///
/// Two keys are equal if and only if they reference the same metatype AND
/// have the same qualifier value (including both being `nil`).
public struct ServiceKey: Hashable, Equatable, CustomStringConvertible, Sendable {

    // MARK: - Stored Properties

    /// Compiler-guaranteed unique identifier for the registered type.
    /// This is the primary discriminator — never rely on type name strings.
    public let typeIdentifier: ObjectIdentifier

    /// Optional qualifier to distinguish multiple registrations of the same type.
    /// Must be non-empty if provided; empty strings are normalized to `nil` at init.
    /// Allocation: single optional String, CoW semantics, no buffer.
    public let qualifier: String?

    /// Human-readable type name for diagnostics and logging only.
    /// Never used in equality or hashing — prevents name-collision attacks.
    /// Allocation: single String, CoW semantics, no buffer.
    public let typeName: String

    // MARK: - Initializer

    /// Creates a service key for the given type and optional qualifier.
    ///
    /// - Parameters:
    ///   - type: The Swift metatype to register against.
    ///   - qualifier: An optional string to distinguish multiple registrations of the same type.
    ///                Empty strings are treated as `nil` (deny ambiguous input).
    ///
    /// - Note: The qualifier is validated and trimmed. Whitespace-only qualifiers are rejected (normalized to nil).
    public init<T>(_ type: T.Type, qualifier: String? = nil) {
        self.typeIdentifier = ObjectIdentifier(type)
        self.typeName = String(describing: type)

        // Validate qualifier: trim whitespace, reject empty/whitespace-only strings.
        // This prevents silent registration collisions from " " vs "" vs nil.
        if let raw = qualifier {
            let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            self.qualifier = trimmed.isEmpty ? nil : trimmed
        } else {
            self.qualifier = nil
        }
    }

    // MARK: - Equatable

    /// Equality is determined solely by typeIdentifier and qualifier.
    /// typeName is explicitly excluded — it is for diagnostics only.
    public static func == (lhs: ServiceKey, rhs: ServiceKey) -> Bool {
        lhs.typeIdentifier == rhs.typeIdentifier && lhs.qualifier == rhs.qualifier
    }

    // MARK: - Hashable

    /// Hash combines only typeIdentifier and qualifier.
    /// typeName is excluded to maintain consistency with `==`.
    public func hash(into hasher: inout Hasher) {
        hasher.combine(typeIdentifier)
        hasher.combine(qualifier)
    }

    // MARK: - CustomStringConvertible

    /// Human-readable description for logging. Never includes sensitive data.
    public var description: String {
        if let qualifier {
            return "ServiceKey(\(typeName), qualifier: \"\(qualifier)\")"
        }
        return "ServiceKey(\(typeName))"
    }
}


// App/Composition/ServiceScope.swift
// Forge Platform — Dependency Injection Core
// Defines service lifetime semantics for the DI container.
//
// Security assumptions:
// - Scope is a value type (enum), Sendable, and immutable.
// - Scoped lifetimes use a string scope identifier; validated at registration time.
// - No heap allocations beyond the scope name string (CoW).

import Foundation

/// Defines the lifetime semantics of a service registration within the container.
///
/// - `transient`: A new instance is created on every resolution. No caching.
/// - `singleton`: A single instance is created on first resolution and reused for the container's lifetime.
/// - `scoped`: An instance is created once per named scope and reused within that scope.
public enum ServiceScope: Sendable, CustomStringConvertible {

    /// A new instance is created for every resolution request.
    /// No reference is retained by the container after resolution.
    case transient

    /// A single instance is lazily created on first resolution and cached
    /// for the lifetime of the container. Thread safety is guaranteed by
    /// the container actor.
    case singleton

    /// An instance is created once per named scope and reused within that scope.
    /// The scope name is validated: empty/whitespace-only names are rejected at registration.
    /// Allocation: single String per scoped registration, CoW semantics.
    case scoped(String)

    // MARK: - CustomStringConvertible

    /// Human-readable description for diagnostics. Never includes sensitive data.
    public var description: String {
        switch self {
        case .transient:
            return "transient"
        case .singleton:
            return "singleton"
        case .scoped(let name):
            return "scoped(\"\(name)\")"
        }
    }

    /// Whether this scope retains instances after resolution.
    /// Transient scopes never cache; singleton and scoped do.
    public var isCached: Bool {
        switch self {
        case .transient:
            return false
        case .singleton, .scoped:
            return true
        }
    }
}


// App/Composition/ServiceRegistration.swift
// Forge Platform — Dependency Injection Core
// Encapsulates a single service registration: its factory, scope, and metadata.
//
// Security assumptions:
// - The factory closure is @Sendable to ensure safe cross-actor usage.
// - Factory closures must not capture mutable external state.
// - The resolved singleton cache is managed exclusively by the container actor;
//   ServiceRegistration itself does not cache.
// - No large buffers or caches allocated here. One closure + metadata per registration.

import Foundation

/// Errors that can occur during service registration validation.
public enum ServiceRegistrationError: LocalizedError, Sendable {
    /// The scoped lifetime was given an empty or whitespace-only scope name.
    case invalidScopeName(key: ServiceKey)
    /// A duplicate registration was attempted without explicit override.
    case duplicateRegistration(key: ServiceKey)
    /// The factory produced nil or a type mismatch.
    case factoryReturnedInvalidType(key: ServiceKey, expectedType: String)

    public var errorDescription: String? {
        switch self {
        case .invalidScopeName(let key):
            return "Invalid scope name for service registration: \(key). Scoped registrations require a non-empty scope identifier."
        case .duplicateRegistration(let key):
            return "Duplicate service registration detected for \(key). Use override parameter to replace explicitly."
        case .factoryReturnedInvalidType(let key, let expectedType):
            return "Factory for \(key) returned invalid type. Expected: \(expectedType)."
        }
    }
}

/// A type-erased service factory that produces instances via the container's resolver.
/// Allocation: one closure capture per registration. No buffers.
public struct ServiceRegistration: Sendable {

    /// The key identifying which service type (and optional qualifier) this registration satisfies.
    public let key: ServiceKey

    /// The lifetime scope for instances produced by this registration.
    public let scope: ServiceScope

    /// Type-erased, sendable, async factory closure.
    /// Accepts a `ServiceResolving` resolver so factories can resolve their own dependencies.
    /// Throws on failure — never returns silently on error (fail-closed).
    ///
    /// Allocation: single closure, captured values must be Sendable.
    public let factory: @Sendable (any ServiceResolving) async throws -> Any

    /// Timestamp of registration for audit trail.
    /// Allocation: 8-byte Date value type.
    public let registeredAt: Date

    /// Creates a validated service registration.
    ///
    /// - Parameters:
    ///   - key: The service key for this registration.
    ///   - scope: The lifetime scope.
    ///   - factory: An async, throwing, sendable factory closure.
    ///
    /// - Throws: `ServiceRegistrationError.invalidScopeName` if a scoped registration has an empty scope name.
    public init(
        key: ServiceKey,
        scope: ServiceScope,
        factory: @escaping @Sendable (any ServiceResolving) async throws -> Any
    ) throws {
        // Validate scoped scope names — fail closed on invalid input.
        if case .scoped(let name) = scope {
            let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else {
                throw ServiceRegistrationError.invalidScopeName(key: key)
            }
        }

        self.key = key
        self.scope = scope
        self.factory = factory
        self.registeredAt = Date()
    }
}


// App/Composition/ServiceResolving.swift
// Forge Platform — Dependency Injection Core
// Protocol defining the resolver interface for the service container.
//
// Security assumptions:
// - Resolution is async throws — callers must handle failures explicitly (fail-closed).
// - No default implementations that silently return nil or placeholder values.
// - Protocol is Sendable-compatible for use across actor boundaries.
// - All resolved types must match the requested type exactly; no implicit casting.

import Foundation

/// Errors that can occur during service resolution.
public enum ServiceResolutionError: LocalizedError, Sendable {
    /// No registration was found for the requested service key.
    case serviceNotFound(key: ServiceKey)
    /// The factory produced a value that could not be cast to the expected type.
    case typeMismatch(key: ServiceKey, expectedType: String, actualType: String)
    /// A circular dependency was detected during resolution.
    case circularDependency(chain: [ServiceKey])
    /// The container has been invalidated or torn down.
    case containerInvalidated

    public var errorDescription: String? {
        switch self {
        case .serviceNotFound(let key):
            return "No service registered for \(key). Ensure the service is registered before resolution."
        case .typeMismatch(let key, let expectedType, let actualType):
            return "Type mismatch resolving \(key): expected \(expectedType), got \(actualType)."
        case .circularDependency(let chain):
            let chainDesc = chain.map(\.description).joined(separator: " → ")
            return "Circular dependency detected: \(chainDesc)."
        case .containerInvalidated:
            return "Service container has been invalidated and cannot resolve services."
        }
    }
}

/// The resolver protocol through which services are retrieved from the container.
///
/// All resolution is async and throwing — callers must handle errors explicitly.
/// There are no silent fallbacks or optional return paths for required services.
public protocol ServiceResolving: Sendable {

    /// Resolves a service of the given type and optional qualifier.
    ///
    /// - Parameters:
    ///   - type: The expected concrete or protocol type.
    ///   - qualifier: An optional qualifier to distinguish multiple registrations.
    ///
    /// - Returns: An instance of the requested type.
    /// - Throws: `ServiceResolutionError` if the service cannot be resolved. Fails closed.
    func resolve<T>(_ type: T.Type, qualifier: String?) async throws -> T

    /// Checks whether a service is registered for the given type and optional qualifier.
    ///
    /// - Parameters:
    ///   - type: The type to check.
    ///   - qualifier: An optional qualifier.
    ///
    /// - Returns: `true` if a registration exists, `false` otherwise.
    func isRegistered<T>(_ type: T.Type, qualifier: String?) -> Bool
}

/// Default qualifier parameter so callers can omit it.
extension ServiceResolving {
    /// Convenience: resolve without qualifier.
    public func resolve<T>(_ type: T.Type) async throws -> T {
        try await resolve(type, qualifier: nil)
    }

    /// Convenience: check registration without qualifier.
    public func isRegistered<T>(_ type: T.Type) -> Bool {
        isRegistered(type, qualifier: nil)
    }
}


// App/Composition/ServiceContainer.swift
// Forge Platform — Dependency Injection Core
// The composition root: a thread-safe, actor-based service container.
//
// Security assumptions:
// - Actor isolation guarantees exclusive access to mutable state (registrations, singletonCache, scopedCaches).
// - Circular dependency detection uses a resolution stack — fails closed on cycles.
// - No force unwraps anywhere. All paths have explicit error handling.
// - Singleton and scoped caches use minimal allocations: Dictionary with ServiceKey keys.
// - The container can be invalidated (torn down), after which all resolutions fail closed.
// - Factory closures are @Sendable; no mutable shared state leaks through them.
//
// Memory budget (OI-13):
// - registrations: Dictionary<ServiceKey, ServiceRegistration> — one entry per registered service.
// - singletonCache: Dictionary<ServiceKey, Any> — one entry per resolved singleton.
// - scopedCaches: Dictionary<String, Dictionary<ServiceKey, Any>> — one sub-dict per scope, one entry per resolved scoped service.
// - resolutionStack: Array<ServiceKey> — transient, only exists during resolution call, max depth = dependency graph depth.
// All allocations are proportional to registration count. No unbounded caches or buffers.

import Foundation

/// Protocol for registering services into the container.
public protocol ServiceRegistering: Sendable {

    /// Registers a service factory for the given type and optional qualifier.
    ///
    /// - Parameters:
    ///   - type: The type to register.
    ///   - qualifier: An optional qualifier string.
    ///   - scope: The lifetime scope for this registration.
    ///   - override: If `true`, replaces any existing registration. If `false`, throws on duplicates. Defaults to `false`.
    ///   - factory: An async, throwing, sendable factory that receives a resolver for sub-dependencies.
    ///
    /// - Throws: `ServiceRegistrationError` on validation failure or duplicate without override.
    func register<T>(
        _ type: T.Type,
        qualifier: String?,
        scope: ServiceScope,
        override: Bool,
        factory: @escaping @Sendable (any ServiceResolving) async throws -> T
    ) throws
}

/// Default parameter extensions for `ServiceRegistering`.
extension ServiceRegistering {
    /// Convenience: register with defaults (no qualifier, transient scope, no override).
    public func register<T>(
        _ type: T.Type,
        qualifier: String? = nil,
        scope: ServiceScope = .transient,
        override: Bool = false,
        factory: @escaping @Sendable (any ServiceResolving) async throws -> T
    ) throws {
        try register(type, qualifier: qualifier, scope: scope, override: override, factory: factory)
    }
}

/// The primary service container — composition root for the Forge application.
///
/// Thread safety is guaranteed by Swift actor isolation. All mutable state
/// (registrations, caches) is accessed exclusively through the actor.
///
/// Usage:
/// ```swift
/// let container = ServiceContainer()
/// try container.register(MyProtocol.self, scope: .singleton) { _ in MyImpl() }
/// let service: MyProtocol = try await container.resolve(MyProtocol.self)
/// ```
public actor ServiceContainer: ServiceResolving, ServiceRegistering {

    // MARK: - State

    /// All active registrations, keyed by ServiceKey.
    /// Allocation: one dictionary, grows linearly with registration count.
    private var registrations: [ServiceKey: ServiceRegistration] = [:]

    /// Cached singleton instances, lazily populated on first resolution.
    /// Allocation: one dictionary, max entries = number of singleton registrations.
    private var singletonCache: [ServiceKey: Any] = [:]

    /// Cached scoped instances, organized by scope name then service key.
    /// Allocation