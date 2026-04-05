package uom.services.benchmarks.config;

import org.neo4j.cypherdsl.core.renderer.Configuration;
import org.neo4j.cypherdsl.core.renderer.Dialect;
import org.springframework.context.annotation.Bean;

@org.springframework.context.annotation.Configuration
public class AppConfig {
  /*
   * Factory bean that creates the org.neo4j.cypherdsl.core.renderer.Configuration
   * instance
   */
  @Bean
  Configuration cypherDslConfiguration() {
    return Configuration.newConfig()
        .withDialect(Dialect.NEO4J_5).build();
  }
}
