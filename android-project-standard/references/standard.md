# Kotlin / Android 项目标准(完整版)

面向 AI 主导开发的 Kotlin/Android 工程标准。与 Python / Rust / Swift 姊妹标准同一条脊:**信任放在可被机器检验的代码上,而非模型。** Kotlin 与 Swift 相近:静态保证大半由编译器免费提供(null-safety、sealed `when` 穷尽、加 `explicitApi()` 后显式的公共 API 面),编译期强制、无类型擦除——但 Kotlin **没有** Rust 的 `Send`/`Sync`、也没有 Swift 6 的编译期 data-race 安全,所以这一格由结构化并发纪律 + detekt 的协程规则兜底。本标准的重点是:把少数逃生舱关上、打开 `allWarningsAsErrors` + `explicitApi()` + detekt error 门、把每个外部依赖推到 interface 后面、结构尽量深且命名即定位、并把人类的隐性兜底外化成会失败的工件。

> **定位**:本标准是**项目级工程标准(总纲 + 工程门 + 架构约定)**,治理 **Kotlin host 内部怎么写**——lint、格式、严格编译、module 结构、provider 缝、测试。它与 **`polyglot-core-standard` 互补**:那条 meta-标准治理**跨语言接缝**(一个 canonical Rust core + 派生的 UniFFI/JNI 绑定:vendored、`linguist-generated`、gate-excluded、never-edited;typed/fallible 的 FFI 边界;composed gate)。两者在 polyglot 仓里组合:polyglot 定义"接缝怎么连",本标准定义"Kotlin 内部怎么写",且本标准的 `./ci.sh` 接入 polyglot 的 `make check-android` 那一格(那一格今天往往是 composed gate 里最弱的一环——只跑 `gradlew compileDebugKotlin`)。

**适用范围(分两层)**:下列约束分为**通用脊**与**AI 触发层**。

- **通用脊**(任何 Kotlin/Android 项目都适用,与是否碰 AI 无关):Kotlin 编译器 null-safety + sealed/`when` 穷尽、`allWarningsAsErrors` + 库 module `explicitApi()`、零警告门(关死 `!!`/未受检 `as`/`lateinit` 滥用/`GlobalScope`)、kotlinx.serialization + `@JvmInline value class` newtype 边界、Gradle module-per-domain + 深命名、version catalog、`Log` + 强类型 `AppConfig`、ktlint + detekt 双门。
- **AI 触发层**(只在项目真的调用 LLM/embedding/向量库时启用):`:domain` interface 缝 + 零-SDK module、`MockProvider` 作默认、classpath 提示词 + 严格渲染、`logProvenance`、约束下沉控制流。

不碰模型的 app/库应全量采用通用脊、整层跳过 AI 层;在那种项目里硬套 `MockProvider` 或提示词嵌入是 cargo-cult,不是合规。

基线:**Kotlin 2.x**(KGP 2.1.0)、Gradle wrapper 8.11.1、AGP 8.7.3、JVM toolchain 17;纯逻辑 module 是 `kotlin("jvm")` library,只有 `:app` 是 `com.android.application`。每个 module `allWarningsAsErrors = true`,库 module 加 `explicitApi()`;**detekt** 1.23.7(逃生舱规则设 `error`)+ **ktlint** 12.1.2(格式,读根 `.editorconfig`);kotlinx.serialization + value class newtype;`gradle/libs.versions.toml` 钉死所有版本;`:app` 用 Hilt + Jetpack Compose + Material3,KSP 跑注解处理。

---

## 1. 唯一的零警告门(完成的唯一判据)

`ci.sh` 一条 `set -euo pipefail` 脚本,人和 agent 共用,按"快→慢"排:

```bash
#!/usr/bin/env bash
set -euo pipefail

GRADLE="./gradlew --no-daemon --stacktrace"

# 1. 格式(ktlint;无输出即通过)
$GRADLE ktlintCheck

# 2. lint + 逃生舱禁令(detekt;`!!`/UnsafeCast/lateinit/GlobalScope 为 error)
$GRADLE detekt

# 3. 编译(allWarningsAsErrors=true → 警告即错误;编译 app + 其依赖的全部 JVM module)
$GRADLE compileDebugKotlin

# 4. 单元测试(离线、Mock 默认、含 smoke + conformance)
$GRADLE test

echo "✓ 全绿"
```

任一项非零即没完成。四道门各司其职:**ktlint** 管格式(`swift-format` / `cargo fmt` 的对应物),**detekt** 管 lint + 逃生舱禁令(`SwiftLint` / `clippy` 的对应物),**`compileDebugKotlin`** 在 `allWarningsAsErrors` 下即 `-Werror`,**`test`** 跑离线 smoke + conformance。两个 lint gate 互补不冗余,都进门、都留着。用 pre-push hook 钉死;CI 镜像同一套;polyglot 仓里这条接 `make check-android`。`make check` 即 `./ci.sh`,`make lint` / `make build` / `make test` / `make fmt`(`ktlintFormat` 写回)是单项快捷入口。

## 2. 静态保证:编译器 + 严格旋钮,逃生舱关死

不需要 mypy/beartype 那种外挂——Kotlin 类型在编译期强制,无类型擦除。"最严"用原生方式表达:**null-safety**(`T` vs `T?` 编译期分离)、**sealed `when` 穷尽**(漏一个分支即编译错)、加 `explicitApi()` 后**公共 API 必须显式 `public`**。这是 Rust/Swift 由编译器免费给的那部分。

**但 Kotlin 缺一格**:没有 Rust 的 `Send`/`Sync`、也没有 Swift 6 的编译期 data-race 安全。这一格由**结构化并发纪律**(协程作用域随生命周期取消,不开 `GlobalScope`)+ **detekt 协程规则**兜底,而非编译器证明。

**每个 module 在自己的 `kotlin {}` 块打开严格旋钮**(per-module 契约,可 grep):

```kotlin
kotlin {
    explicitApi() // 库 module:公共 API 必须显式 public(否则编译报错)
    jvmToolchain(17)
    compilerOptions {
        allWarningsAsErrors.set(true) // 警告即错误(per-module 契约)
    }
}
```

`:app` 是叶子(application,不是 library),只设 `allWarningsAsErrors`,**不**设 `explicitApi`。

**为什么 per-module、不用根 `subprojects { configure<…> }`** —— 这是一个踩坑后的刻意设计决定:在 `subprojects` / 嵌套作用域里,version-catalog 的 `libs` 访问器与 detekt 的 typed extension 访问器不可靠(实测会 `Unresolved reference` / `ExtensionContainer` 报错,`version.set(libs…)` 还会类型错)。所以根 `build.gradle.kts` 只声明全部插件 `apply false`,各 module 在自己的 `plugins {}` 块里 `apply` 并用 typed `detekt {}` / `kotlin {}` 访问器配置:

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.jvm) apply false
    // … kotlin.compose / kotlin.serialization / hilt / ksp …
    alias(libs.plugins.detekt) apply false
    alias(libs.plugins.ktlint) apply false
}
```

ktlint 无需 per-module 配置(读根 `.editorconfig`);detekt 各 module 指向全仓单一 `config/detekt/detekt.yml`:

```kotlin
detekt {
    buildUponDefaultConfig = true
    config.setFrom(rootProject.files("config/detekt/detekt.yml"))
}
```

**逃生舱一律关死**,这是"无逃生舱"的字面实现,全部映射到 detekt 规则(`maxIssues: 0` 下任何命中即整体失败):

- **`!!` 非空断言** —— 禁(`UnsafeCallOnNullableType`,在 `potential-bugs`)。用 `?.` / `requireNotNull(x) { reason }` / 显式分支。
- **未受检 `as` 强转** —— 禁(`UnsafeCast`,在 `potential-bugs`)。用 `as?` + 失败分支(`CastToNullableType` 也设 error)。
- **`lateinit` 滥用** —— 禁(`LateinitUsage`,在 `potential-bugs` —— **不在** `style`)。改构造注入 / 惰性初始化 / 可空 + 显式处理。
- **`GlobalScope`** —— 禁(`GlobalCoroutineUsage`,在 `coroutines`)。用注入的 `CoroutineScope`,守住结构化并发。
- **平台类型泄漏** —— 来自 Java/FFI 的 `T!` 平台类型若直接外溢,null-safety 形同虚设。无单一 detekt 规则;由 `explicitApi()`(公共 API 不能是平台类型)+ 在 adapter 把 Java/FFI 结果**重新定型**(re-type 成 `T` 或 `T?`)联合堵死。

detekt 的两个机制让这套自我加固:`config.validation: true` + `warningsAsErrors: true` 让**配置写错(拼错/放错规则名)本身就失败**——规则名打错不会被悄悄忽略;`build.maxIssues: 0` 让**任何 finding** 都失败。逃生舱规则全部显式 `active: true` + `severity: error`。

**受控出口**:个别站点确需逃生(已 `require` 过的不变量、框架契约),不在全局松绑,而是**逐处显式豁免并写理由**:

```kotlin
@Suppress("UnsafeCallOnNullableType") // URL 在编译期已知合法,失败即编译期 bug
val url = checkNotNull(parsed)
```

这是 Python `# type: ignore[code] # 原因` / Rust `#[allow(clippy::...)] // 原因` / Swift `// swiftlint:disable:next … — 原因` 的 Kotlin 等价物:不是禁止,是让每次逃生**显式、可审计、可 grep**。

## 3. 不静默失败:sealed 错误层级 / `Result<T>`

对照 Rust 的 `Result<T, E>` + `thiserror`、Swift 的 typed throws:Kotlin 用 **sealed 错误层级**(`when` 穷尽由编译器保证)表达同一套"错误是契约的一部分、不能静默吞掉"。

```kotlin
/** provider(LLM / Embedder / 真实 SDK)调用边界的归一化错误。 */
public sealed class ProviderError(message: String) : Exception(message) {
    public class MissingCredentials(detail: String) : ProviderError(detail)
    public class Transport(detail: String) : ProviderError(detail)
    public class InvalidResponse(detail: String) : ProviderError(detail)
}

/** 领域校验错误:外部输入违反类型约束时抛出。 */
public sealed class DomainError(message: String) : Exception(message) {
    public class OutOfRange(value: Int, allowed: IntRange) :
        DomainError("value out of range: $value not in $allowed")
    public class EmptyInput(field: String) : DomainError("empty input: $field")
}
```

纪律:

- **厂商错在 adapter 边界归一**到 `ProviderError`(`MissingCredentials` / `Transport` / `InvalidResponse`):网络/超时/凭据/解码各色 SDK 异常,在 adapter 内 `map` 成这三态之一。
- **程序 bug**(逻辑错、违反不变量)照常 `error(...)` / `require(...)` / `checkNotNull(...)` 上抛,**绝不**塞进降级路径吞掉。这与 Python"程序错照常上抛、外部错归一"、Rust"程序 bug panic、外部错归一 `ProviderError`"一致。
- **detekt `SwallowedException` = error**(在 `exceptions`):`catch` 后丢弃异常即门禁失败。`TooGenericExceptionCaught` / `ThrowingExceptionFromFinally` / `ReturnFromFinally` 一并开启。
- 简单可恢复场景也可直接用标准库 `Result<T>`;穷尽 `when` 分支处理 `onSuccess`/`onFailure`,不裸 `getOrThrow()` 当万能逃生。
- 测试里的断言失败由测试框架报告,不算"静默失败"。

## 4. 边界:parse, don't validate —— kotlinx.serialization + value class newtype

每个跨边界的值(配置、LLM 输出、工具结果、文件、反序列化)在入口处用 **kotlinx.serialization** 解码成强类型值;**把约束编码进 `@JvmInline value class` newtype,让非法状态不可表示**,而非运行时 if 校验。

```kotlin
@Serializable(with = TopKSerializer::class)
@JvmInline
public value class TopK private constructor(public val value: Int) {
    public companion object {
        public val VALID_RANGE: IntRange = 1..100

        /** 构造并校验。@throws DomainError.OutOfRange 当 [value] 不在 [VALID_RANGE]。 */
        public fun of(value: Int): TopK {
            if (value !in VALID_RANGE) throw DomainError.OutOfRange(value, VALID_RANGE)
            return TopK(value)
        }
    }
}

/** 解码即走校验工厂:非法 JSON 在边界就抛,不渗进领域逻辑。 */
internal object TopKSerializer : KSerializer<TopK> {
    override val descriptor: SerialDescriptor = PrimitiveSerialDescriptor("TopK", PrimitiveKind.INT)
    override fun serialize(encoder: Encoder, value: TopK) = encoder.encodeInt(value.value)
    override fun deserialize(decoder: Decoder): TopK = TopK.of(decoder.decodeInt())
}
```

要点:`private constructor` + 工厂 `of(...)` 强制**一切构造走校验**——拿到 `TopK` 即"已校验"的类型证明,下游签名收 `TopK` 就不必再防御性检查。`@JvmInline value class` 是零运行时开销的 newtype(编译后即底层 `Int`),是 Rust newtype / Swift `Codable` newtype 的精确对应。**关键的反漏点**:自定义 `KSerializer` 的 `deserialize` 也走 `TopK.of(...)`——否则 JSON 路径会绕过校验直接 `TopK(rawInt)`,非法值就渗进领域逻辑了。边界可序列化模型用普通 `@Serializable data class`(如 `Document`)。这是 Python pydantic、Rust `serde` + newtype 的 Kotlin 对应。

## 5. 配置:分层强类型 `AppConfig`

`:kernel` 的 `Config.kt`:一个 `@Serializable AppConfig` + 分层加载器。优先级从低到高:**默认值 < 根级 `configs/settings.json` < 环境变量(`APP_` 前缀,`__` 分隔嵌套)**。非法配置在加载时报错(`SerializationException`,不静默吞),不拖到运行期。这是 pydantic-settings / figment 的 Kotlin 对应。

```kotlin
@Serializable
public data class AppConfig(
    val llmProvider: String = "mock",                 // 默认 mock,离线可跑
    val retriever: RetrieverConfig = RetrieverConfig(),
) {
    public companion object {
        private val json = Json { ignoreUnknownKeys = true }

        /** 默认值 < configs/settings.json < 环境变量(APP_ 前缀,__ 分隔嵌套)。 */
        public fun load(
            settingsPath: String = "configs/settings.json",
            env: Map<String, String> = System.getenv(),
        ): AppConfig {
            val file = File(settingsPath)
            val base = if (file.isFile) json.decodeFromString<AppConfig>(file.readText()) else AppConfig()
            return base.withEnvOverrides(env)
        }
    }
}
```

`data class` 的默认值即"无 settings.json、无 env 时也能加载成功"的离线基线——离线测试依赖此。`APP_RETRIEVER__TOP_K=20` 覆盖 `config.retriever.topK`(`__` 分隔嵌套);env 覆盖在 `withEnvOverrides` 里逐项 `copy(...)`。`:kernel` 零 SDK——只 kotlin stdlib + kotlinx.serialization。

## 6. 日志/血缘/隐私:平台无关 `Log`,载荷不落盘

`:kernel` 的 `Log.kt`:一个平台无关的 `Log` 对象。`:kernel` 是纯 `kotlin("jvm")`(非 Android),所以**默认写 stderr**;Android 行为由 `:app` 在启动时注入 sink——kernel 保持平台无关、可离线单测。

```kotlin
public object Log {
    /** 日志落点。默认 stderr;Android 在组合根改成路由到 android.util.Log。 */
    public var sink: (String) -> Unit = { line -> System.err.println(line) }

    public fun info(category: String, message: String) = sink("[$category] $message")

    /** 记录一次 provider 调用的血缘。**只收码值/计数/版本** —— payload 不在此出现。 */
    public fun logProvenance(source: String, impl: String, version: String, count: Int) {
        sink("provenance source=$source impl=$impl version=$version count=$count")
    }
}
```

`:app` 的 `App`(`@HiltAndroidApp`)在 `onCreate` 把 sink 路由到 `android.util.Log`:

```kotlin
@HiltAndroidApp
class App : Application() {
    override fun onCreate() {
        super.onCreate()
        Log.sink = { line -> AndroidLog.i("app", line) }
    }
}
```

纪律:

- **隐私是 API 形状本身**:`logProvenance` 的参数只有 `source` / `impl` / `version` / `count`——**码值、计数、版本号**。payload(答案、原文、向量值、用户输入)**根本没有入参可传进来**。Swift/Rust 靠 `.private` 插值或字段脱敏纪律,Kotlin 这里更进一步:把"隐私不落盘"做成签名约束,而非靠人记得脱敏。把这条写进 `:kernel` 的 CLAUDE.md 当硬纪律。
- **库代码只发事件**,不在库里配置后端;后端(stderr / `android.util.Log`)由组合根注一次 sink。
- `Log.sink` 是启动时设一次的单点,无可变共享状态在热路径上——避开了并发写日志的竞态。

> 血缘进、隐私出 —— 与 §10 的"约束下沉"配套。

## 7. 提示词:classpath 资源 + 严格渲染

提示词放 `:kernel` 的 `src/main/resources/prompts/<domain>/*.md`,用 **classpath 资源**加载(`getResourceAsStream("/prompts/$name.md")`)——随 jar 出厂,dev 与发布一致、无运行时路径问题,对应 Swift `Bundle.module` / Rust `include_str!`。

```kotlin
public sealed class PromptError(message: String) : Exception(message) {
    public class ResourceNotFound(name: String) : PromptError("prompt resource not found: $name")
    public class MissingVariable(key: String) : PromptError("missing prompt variable: $key")
}

public object Prompts {
    public fun load(name: String): String {
        val stream = Prompts::class.java.getResourceAsStream("/prompts/$name.md")
            ?: throw PromptError.ResourceNotFound(name)
        return stream.bufferedReader().use { it.readText() }
    }

    /** 严格渲染:`{{ key }}` 全部替换;模板里出现但未提供的变量直接报错。 */
    public fun render(template: String, variables: Map<String, String>): String {
        // 单出口循环(无 break/continue,满足 detekt ReturnCount):逐个找 `{{ … }}`,
        // 缺值即 throw MissingVariable;无更多占位符时把剩余文本原样输出。
        // …
        val value = variables[key] ?: throw PromptError.MissingVariable(key)
        // …
    }
}
```

**严格渲染**:模板里出现但 `variables` 没提供的占位符,**直接 throw `PromptError.MissingVariable`**,而非静默替成空串——对应 Python Jinja2 `StrictUndefined`、Rust minijinja `UndefinedBehavior::Strict`,契合"不静默失败"。渲染实现刻意写成**单出口循环**(无 `break`/`continue`,满足 detekt `ReturnCount`):未闭合的 `{{` 把剩余文本当字面量。提示词从此随 jar 出厂,改提示词 = 改仓库 + 重新构建(更规范);运行时热换是另一层功能,不在此。

## 8. 结构:Gradle multi-module,module-per-domain

深度来自**module**(多 module),不是一个 module 里堆深文件夹。Gradle module ≈ Cargo crate ≈ SPM target:module 级依赖隔离。"修 reranker"应定位到 `:retrieval/...`,无需搜索。

```
repo/
├── settings.gradle.kts        # 模块注册(Gradle 无 glob,显式 include + 注入哨兵)
├── build.gradle.kts           # 根:全部插件 apply false(各 module 自行 apply)
├── gradle/libs.versions.toml  # version catalog:钉死所有版本(单一矩阵)
├── config/detekt/detekt.yml   # detekt:lint + 逃生舱禁令(!!/as/lateinit/GlobalScope = error)
├── .editorconfig              # ktlint 格式规则
├── ci.sh  Makefile  gradle.properties
├── CLAUDE.md                  # 根级路由表
├── docs/adr/  configs/settings.json  .env.example
├── kernel/    # 跨切面:Config / Log / Prompts(+ CLAUDE.md + resources/prompts/);kotlin("jvm"),零 SDK
├── domain/    # ports(interface)+ model(value class newtype)+ sealed 边界错误;零 SDK / 零框架
├── adapters/  # interface 实现;MockProvider 默认 + ProviderFactory 装配缝(+ 测试:conformance + smoke)
├── retrieval/ generation/  # 领域 feature module(scaffold 按 --domains 生成)
└── app/       # com.android.application:Compose UI + Hilt 组合根
```

要点:

- **module 命名与项目名无关**:`:kernel`/`:domain`/`:adapters`/领域名都是项目无关的;只有 `applicationId`、`namespace`、CLAUDE.md 标题用到 `__APP_ID__`(配合源码包目录占位符 `__PKG_PATH__`,即其 `/` 形式)。基础设施 module 叫 `:kernel` 不叫 `:core`(避开 std/概念冲突)。
- **module 角色**:`:kernel` 跨切面 infra(`kotlin("jvm")`、零外部依赖);`:domain` 纯抽象(`kotlin("jvm")` library、**零 SDK 零框架**);`:adapters` 实现 + `MockProvider` + `ProviderFactory`(`kotlin("jvm")`);领域 feature module 只依赖 `:domain` + `:kernel`;`:app` 唯一的 `com.android.application`(Compose + Hilt 组合根)。
- **依赖方向单向**:领域 feature / `:adapters` → `:domain` + `:kernel`;`:app` → 全部。`:domain` 零 SDK 且**绝不**依赖 `:adapters`(机械可查的不变量,见 §11)。
- **Gradle 没有 Cargo 的 `members = ["crates/*"]` glob**——每个 module 必须在 `settings.gradle.kts` 显式 `include`。因此 scaffold 把领域 module 注入两处哨兵:`settings.gradle.kts` 的 `// __DOMAIN_MODULES__`(追加 `include(":<name>")`)与 `app/build.gradle.kts` 的 `// __DOMAIN_APP_DEPS__`(追加 `implementation(project(":<name>"))`)。模板零领域时依然可构建。

### 8.1 每个 module 一个 CLAUDE.md(分层上下文)

把"分层上下文"落到目录:根 `CLAUDE.md` 是**路由表**(只放硬约束 + 去哪找 + polyglot 边界),每个 module 目录的 `CLAUDE.md` 写本 module 的职责、依赖方向、本地契约(`:domain` 的"零 SDK 零框架"、`:adapters` 的"错误归一 + 默认 Mock"、`:kernel` 的"payload 绝不进 Log")。`check_conformance.py` 要求**每个 module 都有**。好处:agent 进到某 module 工作时,就近拿到的是这一层的精确约束,而非读一份大文档被噪声稀释。

### 8.2 可导航性

命名即路径,是导航层面的"类型即接口契约";Gradle 把它提到 module 级。按能力分(不按 `models/`/`utils/` 分),一直拆到叶子文件只剩单一职责。深结构 + 一致命名,让"哪段代码在哪"无需搜索。

## 9. 模型无关:provider interface 缝 + 零-SDK 的 `:domain` + Hilt 组合根

模型是可热插拔的商品。把正确性、可测性、可审计性从具体模型里抽出来,钉在 interface 与确定性代码上。

- **每个外部依赖 = `:domain` 里一个最小 interface**(`Llm`/`Embedder`/`Reranker`/向量库/解析器),方法 `suspend`(语言关键字,零依赖),失败抛 `ProviderError`。领域逻辑只依赖 interface:

```kotlin
public interface Llm {
    /** @throws ProviderError provider 调用失败时(在 adapter 边界归一)。 */
    public suspend fun complete(prompt: String): String
}

public interface Embedder {
    public suspend fun embed(texts: List<String>): List<List<Double>>
}
```

- **`MockProvider` 作默认实现(不是测试桩)**:确定性、离线、无需 key、零 SDK。可执行、测试、CI 默认走 Mock,跑得快、稳、免费、不被随机性污染:

```kotlin
public class MockLlm : Llm {
    override suspend fun complete(prompt: String): String = "[mock] ${prompt.take(MAX_ECHO)}"
    private companion object { const val MAX_ECHO = 40 }
}
```

- **`ProviderFactory` 是装配缝**:按 config 字符串选实现,默认 `mock`,**未知 provider 显式抛错,绝不沉默回退**:

```kotlin
public object ProviderFactory {
    public fun makeLlm(provider: String): Llm =
        when (provider) {
            "mock" -> MockLlm()
            // "openai" -> OpenAiLlm()   // 仅当 gated :adapters-openai 启用时解开
            else -> throw ProviderError.InvalidResponse("unknown llmProvider: $provider")
        }
}
```

- **缝映射到 Hilt**:interface 在 `:domain`,默认实现(Mock)在 `:adapters`,**唯一的装配点是 `:app` 的 Hilt 组合根** `di/AppModule.kt`——`@Provides` 调 `ProviderFactory` 按 `config` 选实现并注入下游。这是 Python `ports/factory.py`、Rust `app` 组装根 `match`、Swift `App` 组装根的 Kotlin 对应:

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides @Singleton fun provideConfig(): AppConfig = AppConfig.load()
    @Provides @Singleton fun provideLlm(config: AppConfig): Llm = ProviderFactory.makeLlm(config.llmProvider)
    @Provides @Singleton fun provideEmbedder(config: AppConfig): Embedder = ProviderFactory.makeEmbedder(config.llmProvider)
}
```

- **`:domain` 零 SDK / 零框架**(机械可查):`check_conformance.py` 文本解析 `domain/build.gradle.kts`,撞上 SDK 黑名单(`openai`/`anthropic`/`langchain4j`/`pinecone`/`onnxruntime` 等)或框架 token(`com.android`/`compose`/`hilt`/`dagger`/`androidx`)即报错。`:domain` 是纯 `kotlin("jvm")` library。
- **真实 SDK 在 gated 的独立 module**:真实后端如 `:adapters-openai` 是单独 module,依赖 SDK,由 **Gradle property 门控**——在 `settings.gradle.kts` 按 property 决定是否 `include`,默认 build 不含、不拉 SDK。这是 Cargo features / SPM traits 的 Kotlin 对应:

```kotlin
// settings.gradle.kts(示意):gradle property 门控真实后端,默认完全离线
if (providers.gradleProperty("realProviders").isPresent) {
    include(":adapters-openai")
}
```

adapter 内把厂商各色错误**归一到 `ProviderError`**(`Transport` / `InvalidResponse` / `MissingCredentials`);程序 bug 照常上抛。

- **一致性契约(conformance kit,`:adapters` 的 `ProviderConformanceTest`)**:任何号称实现某 port 的类型(Mock 与真实后端)都跑同一组行为不变量——可插拔只在所有实现行为一致时才安全。Mock 与真实后端列进同一 `List<Pair<String, () -> Embedder>>`,共享断言:确定性(同输入同输出)、保持输入数量、非空向量、非空 completion:

```kotlin
@Test
fun embedderIsDeterministic() = runTest {
    for ((name, make) in embedders) {
        val embedder = make()
        assertEquals(embedder.embed(listOf("hello", "world")), embedder.embed(listOf("hello", "world")), "$name 应确定性")
    }
}
```

- **离线 smoke(`SmokeTest`)**:无 key、离线跑通主链路——默认 config + Mock + 严格提示词渲染 + newtype 校验,并断言"未知 provider 抛错(无沉默回退)""缺变量抛 `MissingVariable`""`TopK.of(0)` / `TopK.of(101)` 抛 `OutOfRange`"。设成硬验收。

## 10. 让 AI 输出可信:约束下沉控制流,而非写进 Prompt

Prompt 是软约束,温度/越狱/长上下文都能绕过;只有沉到代码的约束才从"概率性遵守"变成"结构上不可能违反"。本节偏原则(不像结构那样能完全机械检验),但对 AI-touching 代码是上位纪律。

- **Constrain, don't ask**:对不可妥协属性(不编造、必引用、不越权),让模型物理上无法违反——命中事实时答案由代码从结构化值确定性合成、模型散文整段丢弃;无事实时编排层改写成"查不到"。迁移:列"绝不能发生"清单,逐条问"模型能否在听话的同时仍违反它",凡"能"的就移出模型。
- **收窄发射面**:不让模型自由生成关键载荷——让它从一个 **Kotlin `sealed class` / `enum`** 里选、或调返回三态(`found`/`notFound`/`unrecognized`)的工具,最终值取自工具结果而非模型文本。`sealed class` + 穷尽 `when` 天然就是受控发射面,且编译器保证你处理了每个 case。
- **安全门确定性、独立、永不可插拔**:理解类(意图解析)可替换;安全决策(越权/敏感隔离)做成确定性代码,从原始输入独立重判,不信任可插拔组件的输出。可替换的是智能,不是护栏。**在 polyglot 仓里,安全门在 core,不在 host**——host 收 typed values 过 FFI,不在 Kotlin 侧重判。
- **血缘进、隐私出**:见 §6(`logProvenance` + 载荷不入参的纪律)。

## 11. 把隐性兜底外化成会失败的工件

人靠经验、记忆判断"做完没""文档过时没";agent 没有这些,只优化能观测到的反馈。每加一个会失败的检查,就把一份隐性知识变成 agent 无法悄悄绕过的硬约束。

- **加宽的零警告门**(§1):ktlint → detekt → `compileDebugKotlin`(`-Werror`)→ test(smoke + conformance)。任一项非零即没完成。人和 agent 共用同一条判据,用 pre-push hook 钉死。
- **`check_conformance.py` 的机械不变量**——管结构(`ci.sh` 那条门管行为与质量)。Gradle 没有 `dump-package` 那样干净的 manifest JSON 出口,故对 `build.gradle.kts` / `settings.gradle.kts` 做**文本/正则**近似检查(与 Swift 用 `swift package dump-package` 不同,但对结构不变量足够)。它检:① 根工程必备文件齐全(`settings.gradle.kts`/`build.gradle.kts`/`libs.versions.toml`/`detekt.yml`/`.editorconfig`/`ci.sh`/`CLAUDE.md`);② multi-module(`include` ≥ 2);③ **每个 module 有 CLAUDE.md**;④ **`:domain` 零 SDK(黑名单子串)+ 零框架(token)+ 不依赖 `:adapters`**;⑤ `allWarningsAsErrors` 配在每个 module 或根;⑥ **`detekt.yml` 把 `UnsafeCallOnNullableType`/`UnsafeCast` 标为 `error` + 有失败阈值(`maxIssues: 0` 或 `failOnSeverity`)**;⑦ `ci.sh` 有 `set -euo pipefail` 且串起 ktlint→detekt→compile(-Werror)→test 四道门;⑧ `libs.versions.toml` 钉了 kotlin + detekt + ktlint;⑨ **若存在生成绑定目录(`uniffi`/`generated`)则它必须在 detekt/ktlint 配置里被排除**。
- **自描述工件从真实代码派生**:依赖图用 `./gradlew :module:dependencies` 内省,而非手画;手维护的图必然腐烂,腐烂的图比没有更危险。
- **分层上下文**(§8.1):根路由表 + 每 module 就近契约,而非一份大文档读到底。上下文窗口稀缺,"什么都塞"稀释信号。

## 12. 驾驭 AI 做大工作:可拆分、可逐步验证、可对抗审查

把 AI 当可监督的劳力,而非无监督自动驾驶。这是工作流层,轻量版规则:

- **先决策再编码(ADR,`docs/adr/`)**:架构/产品决策写成编号、不可变的 ADR(背景 + 选定 + 被否决备选及理由)。AI 最擅长明确约束下填实现,最不可靠的是替你做含糊取舍;否决理由还防它重走已排除的路。
- **TDD 红灯先行,测试即不可动摇的规格**:每个改动先写会失败的测试(JUnit / kotlin.test),再实现到绿,**绝不**为通过而弱化测试;给 subagent 的任务直接附失败测试当验收。
- **拆成编号步骤、每步独立绿灯**:大重构拆有序步骤,每步一次提交、跑完整 `./ci.sh` 再进入下一步,绝不攒巨型 diff——把失败爆炸半径压到一步之内。
- **分解→并行→综合**:主 agent 拆边界清晰、规格完整的子任务并行分派,逐个审 diff 并在提交前过门。
- **对抗式独立复审**:写完后另起独立、带敌意的多视角复审("假设它有错,去证伪"),优先审测试盖不到的产物(图、文档、取舍)。
- **polyglot amplifier**:改 core 契约 = 多 sub-tree 改动。**core 契约改 + 重新生成的绑定 + 各 host 适配 = 一个连贯提交**,绝不在"部分绑定 stale"的中间态拆分提交(否则漂移守卫 fail)。

## 13. 与 polyglot-core-standard 的边界(互补,不重叠)

本标准管 **Kotlin host 内部**;`polyglot-core-standard` 管**跨语言接缝**。在 polyglot 仓里两者组合,职责清晰切分:

- **接缝(polyglot 管)**:core 是 single source of truth(共享逻辑/数据模型只一份,Rust);契约只声明一次,host 绑定是 **derived bindings**(UniFFI 生成 Swift/Kotlin、PyO3 手写),**never hand-mirror**(绝不把 core struct 手抄进 host);FFI 边界 typed & fallible(core `Result<T,E>` → Kotlin checked exception,**no panic crosses FFI**);**composed gate**(`make check` 串各 host gate + 漂移守卫);工具链 + 生成器版本钉死在根 `versions.toml`(本标准的 `libs.versions.toml` 里 kotlin/detekt/ktlint/generator 版本须与之对齐)。
- **内部(本标准管)**:lint / 格式 / strict 编译 / module 结构 / provider 缝 / 测试——即 §1–§12。
- **生成绑定排除(polyglot 第 4 条非协商项)**:UniFFI/JNI 生成的 Kotlin(在 Android host 里通常落在 `:app` 的 `uniffi/` 包)是 **vendored 工件**——`linguist-generated`、gate-excluded、never-edited。两侧都排除:ktlint 经 `.editorconfig` 的 `[**/uniffi/**]` / `[**/generated/**]` 设 `ktlint = disabled`;detekt 在 `:app` 用
  ```kotlin
  tasks.withType<io.gitlab.arturbosch.detekt.Detekt>().configureEach {
      exclude("**/uniffi/**", "**/generated/**")
  }
  ```
  host 的逃生舱禁令(`!!`/`as`)**不**适用于生成文件——治理移到手写 bridge。
- **手写 FFI bridge 是受治理代码**:消费生成类型、把生成异常 re-type 成 host 值的那层(如 claustra 的 `ClaustraBridge.kt`)是**受本标准治理的接缝代码**(关逃生舱、归一异常、用 `typealias` 复用生成类型而非手抄 struct)。生成绑定本身不受治理。
- **门接 `make check-android`**:本 module 的 `./ci.sh` 是 composed gate 里 Android 那一格。
- **AI 缝在调模型的那一个 sub-tree**(通常 core 或独立 worker):若 LLM 活在 core/worker,Kotlin host **spine-only**——收 typed values 过 FFI,不在 host 套 `MockProvider`(那是 cargo-cult)。本标准的 AI 触发层只在 **Kotlin host 自己独立调模型**时才开。

## 14. 按项目规模伸缩:通用脊 vs AI 触发层

module 拆分、每 module CLAUDE.md、ADR、provider 缝都是真实开销——对 200 行小 app 是 overkill。它们是**触发式、可伸缩的模式**,不是一刀切强制:

- **沿两个轴伸缩,不是一个**——规模 × 领域。
- **通用脊**(任何 Kotlin/Android 项目,无论是否碰 AI):编译器严格 + `allWarningsAsErrors` + `explicitApi`、零警告门、sealed 错误 / `Result` + 逃生舱关死、kotlinx.serialization + value class newtype 边界、Gradle module-per-domain + 深命名、version catalog、ktlint + detekt。
- **AI 触发层**(只在真调 LLM/embedding/向量库时开):`:domain` interface 缝 + 零-SDK module、`MockProvider`-as-default、classpath 提示词 + 严格渲染、`logProvenance`、约束下沉。
- 纯 app(从不调模型)应**全量取脊、整层跳过 AI 层**;硬套 `MockProvider` 是 cargo-cult。
- **小项目可单 module 起步**:单 module + 两 lint gate + 零警告门,就是一个完全合格的小规模实例。第二个职责出现时才拆 module;真要调模型时才把它推到 interface 后面。
- **polyglot 仓**:AI 缝在调模型的那一个 sub-tree(通常 core),Kotlin host spine-only,收 typed values 过 FFI。

---

## 附:Python / Rust / Swift 姊妹标准的映射速查

| 关注点 | Python 标准 | Rust 标准 | Swift 标准 | Kotlin/Android 标准 |
|---|---|---|---|---|
| 静态类型 | mypy `--strict` | 编译器(免费) | 编译器(免费,无类型擦除) | 编译器(null-safety;**无 data-race 安全**) |
| 运行时类型 | beartype + claw hook | 不需要 | 不需要(编译期强制) | 不需要(编译期强制) |
| "无逃生舱" | 禁裸 `Any` | `#![forbid(unsafe_code)]` | 关死 `!`/`try!`/`as!`/`@unchecked Sendable` | 关死 `!!`/未受检 `as`/`lateinit`/`GlobalScope`(detekt error)+ `allWarningsAsErrors` + `explicitApi()` |
| 不静默失败 | 无裸 `except`、StrictUndefined | `Result`/`thiserror`、clippy 限 `unwrap` | typed `throws(E)` + 具体 `Error` | sealed `ProviderError`/`DomainError` + `Result`;detekt `SwallowedException`;边界归一 |
| 逃生须记录 | `# type: ignore[code] # 原因` | `#[allow(clippy::...)] // 原因` | `// swiftlint:disable:next … — 原因` | `@Suppress("rule") // 原因` |
| 边界校验 | pydantic | `serde` + newtype | `Codable` + newtype | kotlinx.serialization + `@JvmInline value class` newtype(自定义 KSerializer 走校验工厂) |
| 结构 | src 布局 + 包内 domain-first 深目录 | Cargo workspace + crate-per-domain | SPM package + target-per-domain | Gradle multi-module + module-per-domain |
| 模型无关 | `ports/`+`adapters/`,核心零 SDK | `domain`(trait)+`adapters`,domain 零 SDK | `Domain`(protocol)+`Adapters`,Domain 零 SDK | `:domain`(interface)+`:adapters`,**domain 零 SDK 零框架** |
| 可选后端 | optional extras + lazy import | `optional` 依赖 + feature 门控 | package traits + `.when(traits:)` | gated 独立 module + gradle property 门控 |
| 装配缝 | `ports/factory.py` | `app` 组装根 `match` | `App` 组装根;`any LLM` ↔ `Box<dyn>` | Hilt `@Module @Provides` 组合根 ↔ `any LLM` / `Box<dyn>` |
| 配置 | pydantic-settings + yaml | figment + toml | Codable `AppConfig` + 分层加载 | `@Serializable AppConfig` + 分层加载(默认 < settings.json < env `APP_*`) |
| 日志/血缘/隐私 | logging + log_provenance + SENSITIVE_FIELDS | tracing + log_provenance | `os.Logger` + privacy 插值 + logProvenance | 平台无关 `Log` + `logProvenance`(payload 不入参)+ Android sink 注入 |
| 提示词 | PackageLoader(随 wheel) | `include_str!`(编译期嵌入) | `Bundle.module`(SPM resources) | classpath resources(随 jar)+ 严格渲染 |
| 门禁 | ruff+mypy+drift+pytest | fmt+clippy -D+doc+test+cargo-deny | swift-format + swiftlint + build(-werror)+ test | ktlint + detekt(`maxIssues: 0`)+ compile(-Werror)+ test |
| 分层上下文 | 根 CLAUDE.md + 就近契约 | 根 CLAUDE.md + 每 crate CLAUDE.md | 根 CLAUDE.md + 每 target CLAUDE.md | 根 CLAUDE.md + 每 module CLAUDE.md |
| 脚手架/合规 | scaffold.py / check_conformance.py | scaffold.py / check_conformance.py | scaffold.py / check_conformance.py(`dump-package`) | scaffold.py / check_conformance.py(文本/正则解析 `build.gradle.kts`) |
