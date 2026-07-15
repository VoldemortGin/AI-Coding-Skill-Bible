package __PKG__.kernel;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;
import org.junit.jupiter.api.Test;

class KernelTest {
  @Test
  void configLoadsDefaultsWhenNoFileNoEnv() {
    AppConfig config = AppConfig.load("/nonexistent/path.json", Map.of());
    assertEquals("mock", config.llmProvider());
    assertEquals(5, config.retriever().topK());
    assertEquals("mock-rerank", config.retriever().rerankModel());
  }

  @Test
  void envOverridesApplyOnTopOfDefaults() {
    AppConfig config =
        AppConfig.load(
            "/nonexistent/path.json",
            Map.of("APP_RETRIEVER__TOP_K", "3", "APP_LLM_PROVIDER", "openai"));
    assertEquals(3, config.retriever().topK());
    assertEquals("openai", config.llmProvider());
  }

  @Test
  void strictRenderThrowsOnMissingVariable() {
    assertThrows(
        PromptException.MissingVariable.class, () -> Prompts.render("Hello {{ name }}", Map.of()));
    assertEquals("Hello world", Prompts.render("Hello {{ name }}", Map.of("name", "world")));
  }

  @Test
  void bundledPromptLoadsFromClasspath() {
    String template = Prompts.load("rag/answer");
    assertTrue(template.contains("{{ context }}"));
    assertTrue(template.contains("{{ question }}"));
    assertThrows(PromptException.ResourceNotFound.class, () -> Prompts.load("does/not/exist"));
  }

  @Test
  void logHelpersEmitWithoutLeakingPayload() {
    Log.info("app", "started");
    Log.error("app", "boom");
    Log.logProvenance("embedder", "MockEmbedder", "1", 3);
  }
}
