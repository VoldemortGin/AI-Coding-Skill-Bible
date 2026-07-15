package __PKG__.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class DomainTest {
  @Test
  void topKAcceptsInRangeAndRejectsOutOfRange() {
    assertEquals(10, new TopK(10).value());
    assertThrows(IllegalArgumentException.class, () -> new TopK(0));
    assertThrows(IllegalArgumentException.class, () -> new TopK(101));
  }

  @Test
  void documentExposesFields() {
    Document doc = new Document("id-1", "body");
    assertEquals("id-1", doc.id());
    assertEquals("body", doc.text());
  }

  @Test
  void providerExceptionKindIsExhaustive() {
    assertEquals("missing_credentials", new ProviderException.MissingCredentials("x").kind());
    assertEquals("transport", new ProviderException.Transport("x").kind());
    assertEquals("invalid_response", new ProviderException.InvalidResponse("x").kind());
  }
}
