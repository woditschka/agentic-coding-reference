package bookstore.web.catalog.internal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import bookstore.api.CatalogGrpc;
import bookstore.api.ListBooksResponse;
import bookstore.web.catalog.Book;
import bookstore.web.catalog.CatalogUnavailable;
import io.grpc.Status;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.resilience.annotation.EnableResilientMethods;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

@SpringBootTest(classes = GrpcCatalogClientResilienceTests.Config.class)
class GrpcCatalogClientResilienceTests {

  @Configuration(proxyBeanMethods = false)
  @EnableResilientMethods(proxyTargetClass = true)
  @Import(GrpcCatalogClient.class)
  static class Config {}

  @Autowired private CatalogClient client;

  @MockitoBean private CatalogGrpc.CatalogBlockingStub stub;

  @BeforeEach
  void theStubKeepsItsIdentityWhenGivenADeadline() {
    when(stub.withDeadlineAfter(anyLong(), any())).thenReturn(stub);
  }

  @Test
  void theClientShouldRetryAFailedCallAndReturnTheLaterAnswer() {
    when(stub.listBooks(any()))
        .thenThrow(Status.UNAVAILABLE.asRuntimeException())
        .thenThrow(Status.DEADLINE_EXCEEDED.asRuntimeException())
        .thenReturn(
            ListBooksResponse.newBuilder()
                .addBooks(
                    bookstore.api.Book.newBuilder()
                        .setTitle("Site Reliability Engineering")
                        .setSubtitle("How Google Runs Production Systems"))
                .build());

    assertThat(client.fetchBooks())
        .containsExactly(
            new Book("Site Reliability Engineering", "How Google Runs Production Systems"));
    verify(stub, times(1 + GrpcCatalogClient.MAX_RETRIES)).listBooks(any());
  }

  @Test
  void theClientShouldGiveUpAsUnavailableOnceTheRetriesAreSpent() {
    when(stub.listBooks(any())).thenThrow(Status.UNAVAILABLE.asRuntimeException());

    assertThatThrownBy(client::fetchBooks).isInstanceOf(CatalogUnavailable.class);
    verify(stub, times(1 + GrpcCatalogClient.MAX_RETRIES)).listBooks(any());
  }
}
