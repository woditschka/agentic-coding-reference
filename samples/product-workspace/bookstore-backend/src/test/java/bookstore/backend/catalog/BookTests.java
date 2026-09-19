package bookstore.backend.catalog;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import org.junit.jupiter.api.Test;

class BookTests {

  @Test
  void aBookShouldRefuseABlankTitle() {
    assertThatIllegalArgumentException().isThrownBy(() -> new Book(" ", "Any subtitle"));
  }

  @Test
  void aBookShouldCarryAnEmptySubtitleWhenNoneIsGiven() {
    assertThat(new Book("AI Engineering", null).subtitle()).isEmpty();
  }
}
