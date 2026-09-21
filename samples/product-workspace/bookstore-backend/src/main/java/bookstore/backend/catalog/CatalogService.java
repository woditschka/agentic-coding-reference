package bookstore.backend.catalog;

import bookstore.backend.catalog.repository.BookRepository;
import java.util.List;
import org.springframework.stereotype.Service;

/** The catalog's public face; every transport that serves it goes through here. */
@Service
public class CatalogService {

  private final BookRepository books;

  CatalogService(BookRepository books) {
    this.books = books;
  }

  public List<Book> books() {
    return books.findAll();
  }
}
