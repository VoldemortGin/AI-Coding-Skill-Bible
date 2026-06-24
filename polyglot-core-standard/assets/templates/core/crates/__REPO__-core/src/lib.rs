//! `__REPO__-core` — the canonical domain capability (rust-project-standard).
//!
//! Pure, host-agnostic shared logic + the data model: the single source of truth. There is
//! deliberately NO `uniffi`/`pyo3` here — the core stays binding-free, and the FFI crates
//! (`__REPO__-ffi`, `__REPO__-py`) declare the cross-language contract and translate to/from
//! these types. Every failure is a typed [`CoreError`] (parse, don't validate); the core never
//! panics on bad input, so nothing can unwind across an FFI boundary (non-negotiable 3).
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// A parsed TOTP configuration — the shared data model that crosses every language seam.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TotpConfig {
    pub secret: String,
    pub digits: u8,
    pub period: u64,
    pub algorithm: String,
}

/// Recoverable parse failures. Each host maps this to its idiomatic error at the boundary.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum CoreError {
    #[error("not an otpauth://totp/ URI")]
    BadScheme,
    #[error("missing required parameter: {0}")]
    MissingParam(String),
    #[error("invalid integer for parameter: {0}")]
    InvalidNumber(String),
}

/// Parse an `otpauth://totp/...` URI into a [`TotpConfig`]. Total and fallible — no panics:
/// every error path returns a typed [`CoreError`].
pub fn parse_otpauth(uri: &str) -> Result<TotpConfig, CoreError> {
    let rest = uri.strip_prefix("otpauth://totp/").ok_or(CoreError::BadScheme)?;
    let query = rest.split_once('?').map_or("", |(_, q)| q);

    let mut secret: Option<String> = None;
    let mut digits: u8 = 6;
    let mut period: u64 = 30;
    let mut algorithm = String::from("SHA1");

    for pair in query.split('&').filter(|s| !s.is_empty()) {
        let (key, value) = pair.split_once('=').unwrap_or((pair, ""));
        match key {
            "secret" => secret = Some(value.to_owned()),
            "digits" => {
                digits = value.parse().map_err(|_| CoreError::InvalidNumber("digits".to_owned()))?;
            }
            "period" => {
                period = value.parse().map_err(|_| CoreError::InvalidNumber("period".to_owned()))?;
            }
            "algorithm" => algorithm = value.to_owned(),
            _ => {}
        }
    }

    let secret = secret.ok_or_else(|| CoreError::MissingParam("secret".to_owned()))?;
    Ok(TotpConfig { secret, digits, period, algorithm })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_minimal_uri() {
        let parsed = parse_otpauth("otpauth://totp/ACME:alice?secret=JBSWY3DPEHPK3PXP");
        assert_eq!(
            parsed,
            Ok(TotpConfig {
                secret: "JBSWY3DPEHPK3PXP".to_owned(),
                digits: 6,
                period: 30,
                algorithm: "SHA1".to_owned(),
            })
        );
    }

    #[test]
    fn rejects_bad_scheme() {
        assert_eq!(parse_otpauth("https://example.com"), Err(CoreError::BadScheme));
    }

    #[test]
    fn rejects_missing_secret() {
        assert_eq!(
            parse_otpauth("otpauth://totp/ACME?digits=8"),
            Err(CoreError::MissingParam("secret".to_owned()))
        );
    }

    #[test]
    fn rejects_non_numeric_digits() {
        assert_eq!(
            parse_otpauth("otpauth://totp/ACME?secret=ABC&digits=x"),
            Err(CoreError::InvalidNumber("digits".to_owned()))
        );
    }
}
