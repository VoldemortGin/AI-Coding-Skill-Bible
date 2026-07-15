package __PKG__.adapters;

import __PKG__.domain.Llm;

/** Deterministic, offline default (not a test stub): echoes a truncated prompt head. */
public final class MockLlm implements Llm {
  private static final int MAX_ECHO = 40;

  @Override
  public String complete(String prompt) {
    String head = prompt.length() > MAX_ECHO ? prompt.substring(0, MAX_ECHO) : prompt;
    return "[mock] " + head;
  }
}
