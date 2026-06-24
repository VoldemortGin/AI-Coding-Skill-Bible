//! `__REPO__-py` — the hand-written PyO3 binding layer. Unlike the GENERATED UniFFI posture,
//! this binding IS governed core code (rust-project-standard applies in full) — and it is still
//! the ONE controlled exit from the workspace `#![forbid(unsafe_code)]` (PyO3 emits FFI
//! `unsafe`; Cargo.toml drops the forbid to `deny`).
//!
//! NO PANIC MAY CROSS INTO CPYTHON (non-negotiable 3): a Rust panic here would abort the
//! interpreter, so every [`CoreError`] is converted to a typed `PyErr` and Python always sees
//! an ordinary exception. The host's view of this contract is the DERIVED, drift-guarded stub
//! `python/src/__REPO__/_native.pyi`.
use __REPO___core::CoreError;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Total `CoreError -> PyErr` mapping: the seam where no failure is left to panic.
fn to_pyerr(err: CoreError) -> PyErr {
    match err {
        CoreError::BadScheme | CoreError::MissingParam(_) | CoreError::InvalidNumber(_) => {
            PyValueError::new_err(err.to_string())
        }
    }
}

/// Parse an otpauth URI; return a plain dict that the Python boundary re-types into a pydantic
/// model (parse, don't validate — the Python analog of the Swift `CoreClient` wrapper).
#[pyfunction]
fn parse_otpauth<'py>(py: Python<'py>, uri: &str) -> PyResult<Bound<'py, PyDict>> {
    let config = __REPO___core::parse_otpauth(uri).map_err(to_pyerr)?;
    let dict = PyDict::new(py);
    dict.set_item("secret", config.secret)?;
    dict.set_item("digits", config.digits)?;
    dict.set_item("period", config.period)?;
    dict.set_item("algorithm", config.algorithm)?;
    Ok(dict)
}

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(parse_otpauth, module)?)?;
    Ok(())
}
