package bookstore.web.catalog.client;

import bookstore.web.catalog.Book;
import java.util.List;

/** The outbound port to the backend's catalog; one adapter binds it to a transport. */
public interface CatalogClient {

  List<Book> fetchBooks();
}
