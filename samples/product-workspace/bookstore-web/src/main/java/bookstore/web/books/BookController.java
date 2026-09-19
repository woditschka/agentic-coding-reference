package bookstore.web.books;

import bookstore.web.catalog.CatalogService;
import bookstore.web.catalog.CatalogUnavailable;
import java.util.List;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
class BookController {

  private final CatalogService catalog;

  BookController(CatalogService catalog) {
    this.catalog = catalog;
  }

  @GetMapping("/")
  String books(Model model) {
    try {
      model.addAttribute("books", catalog.books());
    } catch (CatalogUnavailable e) {
      model.addAttribute("books", List.of());
      model.addAttribute("unavailable", true);
    }
    return "books";
  }
}
