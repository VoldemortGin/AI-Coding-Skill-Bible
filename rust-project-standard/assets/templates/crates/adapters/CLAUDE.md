# crate: adapters — 契约

职责:ports(traits)的具体实现。**唯一允许依赖厂商 SDK 的 crate**,且 SDK `optional` + feature 门控。
- 厂商/网络错在此 `map_err` 归一到 `domain::ProviderError`;程序 bug 不静默吞。
- `MockXxx` 是默认实现(确定性、离线、无需 key),供 demo/test/CI。
- 新增后端 = 加一个 `impl domain::ports::X for YBackend`,不改 domain、不改调用方。
