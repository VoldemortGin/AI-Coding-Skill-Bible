// 组合根(composition root):Hilt 在此按 config 选具体实现并注入下游。
// 这是唯一允许"选实现"的地方;默认 Mock(离线),未知 provider 由 ProviderFactory 显式抛错。

package __APP_ID__.app.di

import __APP_ID__.adapters.ProviderFactory
import __APP_ID__.domain.Embedder
import __APP_ID__.domain.Llm
import __APP_ID__.kernel.AppConfig
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides
    @Singleton
    fun provideConfig(): AppConfig = AppConfig.load()

    @Provides
    @Singleton
    fun provideLlm(config: AppConfig): Llm = ProviderFactory.makeLlm(config.llmProvider)

    @Provides
    @Singleton
    fun provideEmbedder(config: AppConfig): Embedder = ProviderFactory.makeEmbedder(config.llmProvider)
}
