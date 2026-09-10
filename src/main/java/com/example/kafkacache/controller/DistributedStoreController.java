package com.example.kafkacache.controller;

import com.example.kafkacache.model.StoredValue;
import com.example.kafkacache.service.DistributedStoreService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * HTTP surface for the distributed key-value store.
 *
 *   PUT    /api/store/{key}   body: {"value":"..."}   -> upsert
 *   GET    /api/store/{key}                            -> read (local store)
 *   DELETE /api/store/{key}                            -> tombstone delete
 *   GET    /api/store                                  -> dump everything
 *
 * The controller is intentionally thin — all the interesting behavior lives in
 * the service. Its job is just to translate HTTP <-> the store API.
 */
@RestController
@RequestMapping("/api/store")
public class DistributedStoreController {

    private final DistributedStoreService storeService;

    public DistributedStoreController(DistributedStoreService storeService) {
        this.storeService = storeService;
    }

    @PutMapping("/{key}")
    public ResponseEntity<StoredValue> put(
            @PathVariable String key,
            @RequestBody Map<String, String> body) {
        String value = body.get("value");
        if (value == null) {
            return ResponseEntity.badRequest().build();
        }
        return ResponseEntity.ok(storeService.put(key, value));
    }

    @GetMapping("/{key}")
    public ResponseEntity<StoredValue> get(@PathVariable String key) {
        // 200 with the value if present in the local store, else 404.
        // Remember: right after a PUT there's a brief window where this can
        // still 404 because the write hasn't propagated to the store yet.
        return storeService.get(key)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{key}")
    public ResponseEntity<Void> delete(@PathVariable String key) {
        storeService.delete(key);
        return ResponseEntity.noContent().build();
    }

    @GetMapping
    public ResponseEntity<List<StoredValue>> getAll() {
        return ResponseEntity.ok(storeService.getAll());
    }
}
