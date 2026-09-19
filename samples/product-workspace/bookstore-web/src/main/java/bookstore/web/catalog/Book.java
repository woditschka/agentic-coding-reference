package bookstore.web.catalog;

/** A book as the page shows it: a title, never blank, and a subtitle that may be empty. */
public record Book(String title, String subtitle) {

  public Book {
    if (title == null || title.isBlank()) {
      throw new IllegalArgumentException("a book has a title");
    }
    subtitle = subtitle == null ? "" : subtitle.strip();
  }
}
