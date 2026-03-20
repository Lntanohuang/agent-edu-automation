package com.edu.platform.chat.config;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.beans.factory.annotation.Qualifier;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class ChatRabbitConfig {

    @Bean
    public Jackson2JsonMessageConverter jackson2JsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory,
                                         Jackson2JsonMessageConverter converter) {
        RabbitTemplate rabbitTemplate = new RabbitTemplate(connectionFactory);
        rabbitTemplate.setMessageConverter(converter);
        return rabbitTemplate;
    }

    @Bean
    public TopicExchange userExchange() {
        return new TopicExchange(ChatMqConstants.USER_EXCHANGE, true, false);
    }

    @Bean
    public TopicExchange aiExchange() {
        return new TopicExchange(ChatMqConstants.AI_EXCHANGE, true, false);
    }

    @Bean
    public DirectExchange userDlxExchange() {
        return new DirectExchange(ChatMqConstants.USER_DLX_EXCHANGE, true, false);
    }

    @Bean
    public DirectExchange aiDlxExchange() {
        return new DirectExchange(ChatMqConstants.AI_DLX_EXCHANGE, true, false);
    }

    @Bean
    public Queue userQueue() {
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", ChatMqConstants.USER_DLX_EXCHANGE);
        args.put("x-dead-letter-routing-key", ChatMqConstants.USER_DLQ_ROUTING_KEY);
        return new Queue(ChatMqConstants.USER_QUEUE, true, false, false, args);
    }

    @Bean
    public Queue userDlq() {
        return new Queue(ChatMqConstants.USER_DLQ, true);
    }

    @Bean
    public Queue aiReplyUserQueue() {
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", ChatMqConstants.AI_DLX_EXCHANGE);
        args.put("x-dead-letter-routing-key", ChatMqConstants.AI_REPLY_USER_DLQ_ROUTING_KEY);
        return new Queue(ChatMqConstants.AI_REPLY_USER_QUEUE, true, false, false, args);
    }

    @Bean
    public Queue aiReplyPersistQueue() {
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", ChatMqConstants.AI_DLX_EXCHANGE);
        args.put("x-dead-letter-routing-key", ChatMqConstants.AI_REPLY_PERSIST_DLQ_ROUTING_KEY);
        return new Queue(ChatMqConstants.AI_REPLY_PERSIST_QUEUE, true, false, false, args);
    }

    @Bean
    public Queue aiReplyUserDlq() {
        return new Queue(ChatMqConstants.AI_REPLY_USER_DLQ, true);
    }

    @Bean
    public Queue aiReplyPersistDlq() {
        return new Queue(ChatMqConstants.AI_REPLY_PERSIST_DLQ, true);
    }

    @Bean
    public Binding userQueueBinding(@Qualifier("userQueue") Queue userQueue,
                                    @Qualifier("userExchange") TopicExchange userExchange) {
        return BindingBuilder.bind(userQueue).to(userExchange).with(ChatMqConstants.USER_ROUTING_KEY);
    }

    @Bean
    public Binding userDlqBinding(@Qualifier("userDlq") Queue userDlq,
                                  @Qualifier("userDlxExchange") DirectExchange userDlxExchange) {
        return BindingBuilder.bind(userDlq).to(userDlxExchange).with(ChatMqConstants.USER_DLQ_ROUTING_KEY);
    }

    @Bean
    public Binding aiReplyUserBinding(@Qualifier("aiReplyUserQueue") Queue aiReplyUserQueue,
                                      @Qualifier("aiExchange") TopicExchange aiExchange) {
        return BindingBuilder.bind(aiReplyUserQueue).to(aiExchange).with(ChatMqConstants.AI_ROUTING_KEY);
    }

    @Bean
    public Binding aiReplyPersistBinding(@Qualifier("aiReplyPersistQueue") Queue aiReplyPersistQueue,
                                         @Qualifier("aiExchange") TopicExchange aiExchange) {
        return BindingBuilder.bind(aiReplyPersistQueue).to(aiExchange).with(ChatMqConstants.AI_ROUTING_KEY);
    }

    @Bean
    public Binding aiReplyUserDlqBinding(@Qualifier("aiReplyUserDlq") Queue aiReplyUserDlq,
                                         @Qualifier("aiDlxExchange") DirectExchange aiDlxExchange) {
        return BindingBuilder.bind(aiReplyUserDlq).to(aiDlxExchange).with(ChatMqConstants.AI_REPLY_USER_DLQ_ROUTING_KEY);
    }

    @Bean
    public Binding aiReplyPersistDlqBinding(@Qualifier("aiReplyPersistDlq") Queue aiReplyPersistDlq,
                                            @Qualifier("aiDlxExchange") DirectExchange aiDlxExchange) {
        return BindingBuilder.bind(aiReplyPersistDlq).to(aiDlxExchange).with(ChatMqConstants.AI_REPLY_PERSIST_DLQ_ROUTING_KEY);
    }
}
