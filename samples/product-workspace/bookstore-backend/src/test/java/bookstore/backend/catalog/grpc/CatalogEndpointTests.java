package bookstore.backend.catalog.grpc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.tuple;

import bookstore.api.Book;
import bookstore.api.CatalogGrpc;
import bookstore.api.ListBooksRequest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.grpc.test.autoconfigure.AutoConfigureTestGrpcTransport;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.grpc.client.ImportGrpcClients;

@SpringBootTest
@AutoConfigureTestGrpcTransport
@ImportGrpcClients(types = CatalogGrpc.CatalogBlockingStub.class)
class CatalogEndpointTests {

  @Autowired private CatalogGrpc.CatalogBlockingStub catalog;

  @Test
  void theEndpointShouldServeEveryStockedTitleOverTheContract() {
    var response = catalog.listBooks(ListBooksRequest.getDefaultInstance());

    assertThat(response.getBooksList())
        .extracting(Book::getTitle, Book::getSubtitle)
        .containsExactly(
            tuple(
                "Designing Data-Intensive Applications",
                "The Big Ideas Behind Reliable, Scalable, and Maintainable Systems"),
            tuple("AI Engineering", "Building Applications with Foundation Models"),
            tuple("Site Reliability Engineering", "How Google Runs Production Systems"));
  }
}
