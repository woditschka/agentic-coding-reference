package bookstore.backend.catalog.grpc;

import bookstore.api.CatalogGrpc;
import bookstore.api.ListBooksRequest;
import bookstore.api.ListBooksResponse;
import bookstore.backend.catalog.Book;
import bookstore.backend.catalog.CatalogService;
import io.grpc.stub.StreamObserver;
import java.util.List;
import org.springframework.grpc.server.service.GrpcService;

/** Serves the catalog contract over gRPC; the mapper keeps the wire shape out of the domain. */
@GrpcService
public class CatalogEndpoint extends CatalogGrpc.CatalogImplBase {

  private final CatalogService catalog;

  CatalogEndpoint(CatalogService catalog) {
    this.catalog = catalog;
  }

  @Override
  public void listBooks(ListBooksRequest request, StreamObserver<ListBooksResponse> response) {
    response.onNext(toResponse(catalog.books()));
    response.onCompleted();
  }

  static ListBooksResponse toResponse(List<Book> books) {
    var response = ListBooksResponse.newBuilder();
    books.forEach(book -> response.addBooks(toBook(book)));
    return response.build();
  }

  private static bookstore.api.Book toBook(Book book) {
    return bookstore.api.Book.newBuilder()
        .setTitle(book.title())
        .setSubtitle(book.subtitle())
        .build();
  }
}
