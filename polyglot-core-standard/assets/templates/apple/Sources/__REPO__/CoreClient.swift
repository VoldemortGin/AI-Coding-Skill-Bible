// CoreClient.swift — the governed FFI seam (polyglot-core-standard non-negotiable 3).
//
// `Generated/__REPO___core.swift` is a VENDORED UniFFI artifact: linguist-generated, excluded
// from swiftlint + swift-format (.swiftlint.yml / Generated/.swift-format-ignore), and NEVER
// hand-edited — a regen wipes any edit. ALL core calls funnel through this thin hand-written
// wrapper, which catches the generated `throws` and re-types it into a host-native value + a
// Swift `enum` error. The escape-hatch bans (no `!`/`try!`/`as!`), strict concurrency, and
// newtype rules apply HERE — not to the generated file. Never hand-copy a core struct: consume
// the generated type, or wrap it in a host newtype as below.

/// Host-native, validated view of the core's TOTP contract (parse, don't validate at the seam).
public struct Totp: Sendable, Equatable {
    public let secret: String
    public let digits: Int
    public let period: Int
    public let algorithm: String
}

/// The core's `OtpError` re-typed into the host's own domain at the boundary.
public enum CoreClientError: Error, Sendable, Equatable {
    case badScheme
    case missingParameter(String)
    case invalidNumber(String)
    case unexpected(String)
}

/// The single entry point hosts use to reach the core. Swift 6 typed `throws`.
public enum CoreClient {
    /// Calls the generated UniFFI function, catches its `throws`, re-types into host values.
    public static func parseOtpauth(_ uri: String) throws(CoreClientError) -> Totp {
        do {
            // `parseOtpauth(uri:)` is the generated global function (lowerCamelCased by UniFFI);
            // the `uri:` label disambiguates it from this label-less static method.
            let config = try parseOtpauth(uri: uri)
            return Totp(
                secret: config.secret,
                digits: Int(config.digits),
                period: Int(config.period),
                algorithm: config.algorithm
            )
        } catch let error as OtpError {
            throw translate(error)
        } catch {
            // No panic can cross the boundary, but stay total: type any unforeseen error too.
            throw .unexpected(String(describing: error))
        }
    }

    private static func translate(_ error: OtpError) -> CoreClientError {
        switch error {
        case .badScheme: .badScheme
        case .missingParam(let name): .missingParameter(name)
        case .invalidNumber(let field): .invalidNumber(field)
        }
    }
}
