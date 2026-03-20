package com.edu.platform.config;

import com.edu.platform.cache.TwoLevelCacheManager;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory redisConnectionFactory) {
        // Redis 基础配置：JSON 序列化，允许缓存 null（TwoLevelCache 用 NullValue.INSTANCE sentinel 防穿透）
        RedisCacheConfiguration baseConfig = RedisCacheConfiguration.defaultCacheConfig()
                .serializeKeysWith(
                        RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(
                        RedisSerializationContext.SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer()));

        RedisCacheManager redisCacheManager = RedisCacheManager.builder(redisConnectionFactory)
                .cacheDefaults(baseConfig.entryTtl(Duration.ofMinutes(30)))
                // 各缓存域自定义 TTL
                .withCacheConfiguration("user", baseConfig.entryTtl(Duration.ofHours(1)))
                .withCacheConfiguration("conversations", baseConfig.entryTtl(Duration.ofMinutes(10)))
                .withCacheConfiguration("questionBank", baseConfig.entryTtl(Duration.ofHours(2)))
                .build();

        return new TwoLevelCacheManager(redisCacheManager);
    }
}
