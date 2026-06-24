//! `__REPO__-ffi` — the ONE place the cross-language UniFFI contract is declared, and the ONE
//! controlled exit from the workspace `#![forbid(unsafe_code)]` (Cargo.toml drops it to
//! `deny`; UniFFI's generated scaffolding carries the per-site `unsafe`). Every host DERIVES
//! its binding from this crate (`make gen-bindings`) — hosts never hand-mirror these types.
//!
//! NO PANIC MAY CROSS THIS BOUNDARY (non-negotiable 3): every `__REPO__-core` failure is
//! converted into a typed [`OtpError`] *before* it reaches a host, so a Rust `panic!` can
//! never unwind into Swift/Kotlin. The `Result -> host-error` mapping below is explicit and
//! total.
use __REPO___core::{CoreError, TotpConfig as CoreTotpConfig};

uniffi::setup_scaffolding!();

/// The TOTP contract as exported to every host (UniFFI Record → Swift struct / Kotlin data class).
#[derive(Debug, Clone, uniffi::Record)]
pub struct TotpConfig {
    pub secret: String,
    pub digits: u8,
    pub period: u64,
    pub algorithm: String,
}

/// The typed, fallible seam: the core's `CoreError` re-typed as a UniFFI error enum. Surfaces
/// as `throws` in Swift / a checked exception in Kotlin — never an abort.
#[derive(Debug, thiserror::Error, uniffi::Error)]
pub enum OtpError {
    #[error("not an otpauth://totp/ URI")]
    BadScheme,
    #[error("missing required parameter: {name}")]
    MissingParam { name: String },
    #[error("invalid integer for parameter: {field}")]
    InvalidNumber { field: String },
}

/// The single exported entry point. Calls the canonical core and maps its typed `Result`
/// across the boundary. `#[uniffi::export]` makes this callable from every generated binding.
#[uniffi::export]
pub fn parse_otpauth(uri: String) -> Result<TotpConfig, OtpError> {
    __REPO___core::parse_otpauth(&uri).map(Into::into).map_err(Into::into)
}

impl From<CoreTotpConfig> for TotpConfig {
    fn from(value: CoreTotpConfig) -> Self {
        Self {
            secret: value.secret,
            digits: value.digits,
            period: value.period,
            algorithm: value.algorithm,
        }
    }
}

impl From<CoreError> for OtpError {
    fn from(value: CoreError) -> Self {
        match value {
            CoreError::BadScheme => Self::BadScheme,
            CoreError::MissingParam(name) => Self::MissingParam { name },
            CoreError::InvalidNumber(field) => Self::InvalidNumber { field },
        }
    }
}
