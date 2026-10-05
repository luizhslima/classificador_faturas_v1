package com.api.service.ingestao.infrastructure.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.server.RequestPredicate;
import org.springframework.web.reactive.function.server.RequestPredicates;
import org.springframework.web.reactive.function.server.RouterFunction;
import org.springframework.web.reactive.function.server.RouterFunctions;
import org.springframework.web.reactive.function.server.ServerResponse;

import com.api.service.ingestao.adapter.in.web.ArquivoHandler;

@Configuration
public class RouterConfig {

    @Bean
    public RouterFunction<ServerResponse> route(ArquivoHandler arquivoHandler) {
        RequestPredicate uploadPredicate = RequestPredicates
                .POST("/v1/datalake/bronze/upload")
                .and(RequestPredicates.accept(MediaType.MULTIPART_FORM_DATA));

        return RouterFunctions.route(uploadPredicate, arquivoHandler::upload);
    }
}
