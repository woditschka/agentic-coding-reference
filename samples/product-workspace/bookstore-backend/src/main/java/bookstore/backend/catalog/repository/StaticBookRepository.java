package bookstore.backend.catalog.repository;

import bookstore.backend.catalog.Book;
import java.util.List;
import org.springframework.stereotype.Repository;

/** The sample's whole stock, fixed at build time; a store replaces this class, nothing else. */
@Repository
public class StaticBookRepository implements BookRepository {

  private static final List<Book> BOOKS =
      List.of(
          new Book(
              "Designing Data-Intensive Applications",
              "The Big Ideas Behind Reliable, Scalable, and Maintainable Systems"),
          new Book("AI Engineering", "Building Applications with Foundation Models"),
          new Book("Site Reliability Engineering", "How Google Runs Production Systems"));

  @Override
  public List<Book> findAll() {
    return BOOKS;
  }
}
