package com.edu.platform.service;

import com.edu.platform.common.BusinessException;
import com.edu.platform.dto.FeedbackRequest;
import com.edu.platform.entity.AiFeedback;
import com.edu.platform.repository.AiFeedbackRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class FeedbackService {

    private final AiFeedbackRepository aiFeedbackRepository;

    @Transactional
    public AiFeedback submit(Long userId, FeedbackRequest request) {
        if (aiFeedbackRepository.existsByUserIdAndMessageId(userId, request.getMessageId())) {
            throw new BusinessException(400, "已提交过反馈");
        }

        AiFeedback feedback = new AiFeedback();
        feedback.setUserId(userId);
        feedback.setConversationId(request.getConversationId());
        feedback.setMessageId(request.getMessageId());
        feedback.setRating(request.getRating());
        feedback.setComment(request.getComment());
        feedback.setConfidence(request.getConfidence());

        return aiFeedbackRepository.save(feedback);
    }
}
