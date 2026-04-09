package com.edu.platform;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.amqp.RabbitAutoConfiguration;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication(exclude = RabbitAutoConfiguration.class)
@EnableCaching
@EnableJpaAuditing
@EnableAsync
public class EduPlatformApplication {

    public static void main(String[] args) {
        SpringApplication.run(EduPlatformApplication.class, args);
    }
}
