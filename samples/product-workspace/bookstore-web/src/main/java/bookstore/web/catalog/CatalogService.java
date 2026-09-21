package bookstore.web.catalog;

import bookstore.web.catalog.client.CatalogClient;
import java.util.List;
import org.springframework.stereotype.Service;

/** The catalog as the rest of the application sees it; the transport stays inside the module. */
@Service
public class CatalogService {

  private final CatalogClient client;

  CatalogService(CatalogClient client) {
    this.client = client;
  }

  public List<Book> books() {
    return client.fetchBooks();
  }
}
