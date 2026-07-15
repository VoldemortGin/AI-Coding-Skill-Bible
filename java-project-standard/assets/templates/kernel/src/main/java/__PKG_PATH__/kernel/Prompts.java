package __PKG__.kernel;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.jspecify.annotations.Nullable;

/**
 * Prompt loading (classpath resources, shipped in the jar) + strict rendering (missing var -&gt;
 * throw).
 */
public final class Prompts {
  private Prompts() {}

  /** Load a bundled prompt's raw text (path relative to resources/prompts/, e.g. "rag/answer"). */
  public static String load(String name) {
    String path = "/prompts/" + name + ".md";
    try (@Nullable InputStream stream = Prompts.class.getResourceAsStream(path)) {
      if (stream == null) {
        throw new PromptException.ResourceNotFound(name);
      }
      return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
    } catch (java.io.IOException e) {
      throw new java.io.UncheckedIOException("failed reading prompt: " + name, e);
    }
  }

  /** Strict render: every {{ key }} is replaced; a referenced-but-missing variable throws. */
  public static String render(String template, Map<String, String> variables) {
    StringBuilder out = new StringBuilder();
    int index = 0;
    while (index < template.length()) {
      int open = template.indexOf("{{", index);
      int close = open < 0 ? -1 : template.indexOf("}}", open + 2);
      if (open < 0 || close < 0) {
        out.append(template, index, template.length());
        index = template.length();
      } else {
        out.append(template, index, open);
        String key = template.substring(open + 2, close).trim();
        @Nullable String value = variables.get(key);
        if (value == null) {
          throw new PromptException.MissingVariable(key);
        }
        out.append(value);
        index = close + 2;
      }
    }
    return out.toString();
  }

  public static String renderNamed(String name, Map<String, String> variables) {
    return render(load(name), variables);
  }
}
