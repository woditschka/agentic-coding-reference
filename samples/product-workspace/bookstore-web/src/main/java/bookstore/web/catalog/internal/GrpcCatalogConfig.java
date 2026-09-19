package bookstore.web.catalog.internal;

import bookstore.api.CatalogGrpc;
import org.springframework.context.annotation.Configuration;
import org.springframework.grpc.client.ImportGrpcClients;
import org.springframework.resilience.annotation.EnableResilientMethods;

/**
 * Imports the contract's blocking stub on the channel named in spring.grpc.client.channel.catalog
 * and switches on the retry and concurrency-limit interceptors the adapter declares.
 */
@Configuration(proxyBeanMethods = false)
@ImportGrpcClients(target = "catalog", types = CatalogGrpc.CatalogBlockingStub.class)
@EnableResilientMethods(proxyTargetClass = true)
class GrpcCatalogConfig {}
