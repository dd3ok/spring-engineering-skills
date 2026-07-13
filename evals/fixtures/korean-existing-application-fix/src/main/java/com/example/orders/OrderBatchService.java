package com.example.orders;

import java.util.List;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderBatchService {

    private final JdbcTemplate jdbcTemplate;

    public OrderBatchService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Transactional
    public void importBatch(List<String> orderIds) {
        orderIds.forEach(this::importOne);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void importOne(String orderId) {
        jdbcTemplate.update("insert into imported_order(id) values (?)", orderId);
    }
}
