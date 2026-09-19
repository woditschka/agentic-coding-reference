package bookstore.web.catalog.internal;

import static org.assertj.core.api.Assertions.assertThat;

import bookstore.api.ListBooksResponse;
import bookstore.web.catalog.Book;
import org.junit.jupiter.api.Test;

class GrpcCatalogClientTests {

  @Test
  void theMapperShouldKeepEveryBookInOrderAndDropOneWithoutATitle() {
    var response =
        ListBooksResponse.newBuilder()
            .addBooks(book("AI Engineering", "Building Applications with Foundation Models"))
            .addBooks(book(" ", "An orphaned subtitle"))
            .addBooks(book("Site Reliability Engineering", "How Google Runs Production Systems"))
            .build();

    assertThat(GrpcCatalogClient.fromResponse(response))
        .containsExactly(
            new Book("AI Engineering", "Building Applications with Foundation Models"),
            new Book("Site Reliability Engineering", "How Google Runs Production Systems"));
  }

  private static bookstore.api.Book book(String title, String subtitle) {
    return bookstore.api.Book.newBuilder().setTitle(title).setSubtitle(subtitle).build();
  }
}
