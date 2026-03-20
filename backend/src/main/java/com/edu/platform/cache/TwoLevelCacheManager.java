package com.edu.platform.cache;

import com.github.benmanes.caffeine.cache.Caffeine;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.data.redis.cache.RedisCache;
import org.springframework.data.redis.cache.RedisCacheManager;

import java.time.Duration;
import java.util.Collection;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class TwoLevelCacheManager implements CacheManager {

    private final RedisCacheManager redisCacheManager;
    private final Map<String, TwoLevelCache> cacheMap = new ConcurrentHashMap<>();

    // Caffeine 配置：最多 10000 条，5 分钟过期
    private final com.github.benmanes.caffeine.cache.Caffeine<Object, Object> caffeineSpec =
            Caffeine.newBuilder()
                    .maximumSize(10_000)
                    .expireAfterWrite(Duration.ofMinutes(5))
                    .recordStats();

    public TwoLevelCacheManager(RedisCacheManager redisCacheManager) {
        this.redisCacheManager = redisCacheManager;
    }

    @Override
    public Cache getCache(String name) {
        return cacheMap.computeIfAbsent(name, this::createTwoLevelCache);
    }

    @Override
    public Collection<String> getCacheNames() {
        return cacheMap.keySet();
    }

    private TwoLevelCache createTwoLevelCache(String name) {
        RedisCache redisCache = (RedisCache) redisCacheManager.getCache(name);
        if (redisCache == null) {
            throw new IllegalStateException("Cannot find RedisCache for name: " + name);
        }
        return new TwoLevelCache(name, caffeineSpec.build(), redisCache);
    }
}
