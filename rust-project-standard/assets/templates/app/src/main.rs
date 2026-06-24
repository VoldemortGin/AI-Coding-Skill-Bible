//! 组装根(composition root):读配置、初始化日志、按配置构造 provider 并注入运行。
use anyhow::{Context, Result};
use domain::ports::Llm;
use kernel::config::Settings;

/// 唯一装配缝:按配置选 LLM 实现。默认 mock,未知配置显式报错。
fn make_llm(settings: &Settings) -> Result<Box<dyn Llm>> {
    match settings.llm_provider.as_str() {
        "mock" => Ok(Box::new(adapters::mock::MockLlm)),
        #[cfg(feature = "openai")]
        "openai" => Ok(Box::new(adapters::openai::OpenAiLlm::new()?)),
        other => anyhow::bail!("未知 llm_provider: {other}"),
    }
}

fn main() -> Result<()> {
    kernel::logging::init();
    let settings = Settings::load().context("加载配置失败")?;
    let llm = make_llm(&settings)?;
    tracing::info!(provider = %settings.llm_provider, "started");
    let answer = llm.complete("ping")?;
    println!("{answer}");
    Ok(())
}
