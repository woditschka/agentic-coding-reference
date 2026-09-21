package bookstore.backend.catalog.repository;

import bookstore.backend.catalog.Book;
import java.util.List;

/** The catalog's persistence boundary; the sample binds it to a fixed list. */
public interface BookRepository {

  List<Book> findAll();
}
