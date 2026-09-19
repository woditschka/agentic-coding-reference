package bookstore.web.catalog;

/** The backend did not answer within the adapter's budget; the page degrades instead of failing. */
public class CatalogUnavailable extends RuntimeException {

  public CatalogUnavailable(Throwable cause) {
    super("the catalog is unavailable", cause);
  }
}
