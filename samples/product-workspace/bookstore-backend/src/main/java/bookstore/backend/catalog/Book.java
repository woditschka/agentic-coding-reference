package bookstore.backend.catalog;

/** A book in the catalog: a title, never blank, and a subtitle that may be empty. */
public record Book(String title, String subtitle) {

  public Book {
    if (title == null || title.isBlank()) {
      throw new IllegalArgumentException("a book has a title");
    }
    subtitle = subtitle == null ? "" : subtitle.strip();
  }
}
