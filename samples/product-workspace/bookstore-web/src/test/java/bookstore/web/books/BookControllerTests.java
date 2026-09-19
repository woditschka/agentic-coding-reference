package bookstore.web.books;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import bookstore.web.catalog.Book;
import bookstore.web.catalog.CatalogService;
import bookstore.web.catalog.CatalogUnavailable;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

@WebMvcTest(BookController.class)
class BookControllerTests {

  @Autowired private MockMvcTester mvc;

  @MockitoBean private CatalogService catalog;

  @Test
  void thePageShouldListEveryBookTheCatalogReturns() {
    when(catalog.books())
        .thenReturn(
            List.of(
                new Book("AI Engineering", "Building Applications with Foundation Models"),
                new Book("Site Reliability Engineering", "How Google Runs Production Systems")));

    assertThat(mvc.get().uri("/"))
        .hasStatusOk()
        .bodyText()
        .contains(
            "AI Engineering",
            "Building Applications with Foundation Models",
            "Site Reliability Engineering",
            "How Google Runs Production Systems");
  }

  @Test
  void thePageShouldSayTheCatalogIsUnavailableInsteadOfFailing() {
    when(catalog.books()).thenThrow(new CatalogUnavailable(new RuntimeException("down")));

    assertThat(mvc.get().uri("/")).hasStatusOk().bodyText().contains("unavailable");
  }
}
