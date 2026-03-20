package com.edu.platform.cache;

import com.github.benmanes.caffeine.cache.Cache;
import org.springframework.cache.support.AbstractValueAdaptingCache;
import org.springframework.cache.support.NullValue;
import org.springframework.data.redis.cache.RedisCache;
import org.springframework.lang.NonNull;
import org.springframework.lang.Nullable;

import java.util.concurrent.Callable;

public class TwoLevelCache extends AbstractValueAdaptingCache {

    private final String name;
    private final Cache<Object, Object> caffeineCache;
    private final RedisCache redisCache;

    public TwoLevelCache(String name, Cache<Object, Object> caffeineCache, RedisCache redisCache) {
        super(true);
        this.name = name;
        this.caffeineCache = caffeineCache;
        this.redisCache = redisCache;
    }

    @Override
    @NonNull
    public String getName() {
        return name;
    }

    @Override
    @NonNull
    public Object getNativeCache() {
        return this;
    }

    /**
     * 返回 store value（含 NullValue.INSTANCE sentinel）。
     * AbstractValueAdaptingCache.get(key) 会调用 fromStoreValue() 将 sentinel 转为 null。
     */
    @Override
    @Nullable
    protected Object lookup(@NonNull Object key) {
        // 先查 L1 Caffeine（可能存有 NullValue.INSTANCE sentinel）
        Object value = caffeineCache.getIfPresent(key);
        if (value != null) {
            return value;
        }
        // 再查 L2 Redis
        ValueWrapper redisValue = redisCache.get(key);
        if (redisValue != null) {
            // 回填 L1，null 值用 sentinel 存储
            Object storeVal = redisValue.get() != null ? redisValue.get() : NullValue.INSTANCE;
            caffeineCache.put(key, storeVal);
            return storeVal;
        }
        return null;
    }

    @Override
    public void put(@NonNull Object key, @Nullable Object value) {
        // L1：null 用 sentinel 存储
        caffeineCache.put(key, value != null ? value : NullValue.INSTANCE);
        // L2：Redis 允许存 null（CacheConfig 中不调用 disableCachingNullValues）
        redisCache.put(key, value);
    }

    @Override
    public void evict(@NonNull Object key) {
        // 先清 L1 再清 L2，缩短不一致窗口（N4 建议）
        caffeineCache.invalidate(key);
        redisCache.evict(key);
    }

    @Override
    public void clear() {
        caffeineCache.invalidateAll();
        redisCache.clear();
    }

    /**
     * 使用父类 get(key) 处理 sentinel → null 转换，避免直接返回 NullValue.INSTANCE（B3 修复）。
     */
    @Override
    @SuppressWarnings("unchecked")
    public <T> T get(@NonNull Object key, @NonNull Callable<T> valueLoader) {
        ValueWrapper wrapper = get(key);
        if (wrapper != null) {
            return (T) wrapper.get();
        }
        try {
            T loaded = valueLoader.call();
            put(key, loaded);
            return loaded;
        } catch (Exception e) {
            throw new ValueRetrievalException(key, valueLoader, e);
        }
    }
}
