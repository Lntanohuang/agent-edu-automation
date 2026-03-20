package com.edu.platform.chat;

import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * 纯单元测试基类：仅启用 Mockito，无 Spring 上下文，运行极快。
 */
@ExtendWith(MockitoExtension.class)
public abstract class BaseUnitTest {
}
