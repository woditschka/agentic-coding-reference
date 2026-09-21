package bookstore.web.catalog.client;

import bookstore.api.CatalogGrpc;
import bookstore.api.ListBooksRequest;
import bookstore.api.ListBooksResponse;
import bookstore.web.catalog.Book;
import bookstore.web.catalog.CatalogUnavailable;
import io.grpc.StatusRuntimeException;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.springframework.resilience.annotation.ConcurrencyLimit;
import org.springframework.resilience.annotation.Retryable;
import org.springframework.stereotype.Component;

/**
 * Binds the catalog port to the gRPC contract. Every call carries a deadline; a failed call is
 * retried with backoff because the read is idempotent; at most a handful run at once, so a slow
 * backend cannot absorb every request thread; the mapper keeps the wire shape out of the domain.
 */
@Component
public class GrpcCatalogClient implements CatalogClient {

  static final long DEADLINE_SECONDS = 2;
  static final int MAX_RETRIES = 2;
  static final int CONCURRENT_CALLS = 8;

  private final CatalogGrpc.CatalogBlockingStub stub;

  GrpcCatalogClient(CatalogGrpc.CatalogBlockingStub stub) {
    this.stub = stub;
  }

  @Override
  @Retryable(
      includes = CatalogUnavailable.class,
      maxRetries = MAX_RETRIES,
      delay = 100,
      multiplier = 2)
  @ConcurrencyLimit(CONCURRENT_CALLS)
  public List<Book> fetchBooks() {
    try {
      return fromResponse(
          stub.withDeadlineAfter(DEADLINE_SECONDS, TimeUnit.SECONDS)
              .listBooks(ListBooksRequest.getDefaultInstance()));
    } catch (StatusRuntimeException e) {
      throw new CatalogUnavailable(e);
    }
  }

  static List<Book> fromResponse(ListBooksResponse response) {
    return response.getBooksList().stream()
        .filter(book -> !book.getTitle().isBlank())
        .map(book -> new Book(book.getTitle(), book.getSubtitle()))
        .toList();
  }
}
