/*
 * SchemeService.java
 * -------------------
 * SchemeMatch AI - Java Supporting Service
 *
 * ROLE OF THIS COMPONENT (explain this to the jury):
 * This is a small, standalone Java microservice that performs profile
 * data validation and normalization BEFORE the Python matching engine
 * runs. It represents the "Java" requirement as a meaningful supporting
 * service in the architecture: Python (Flask) sends the submitted
 * entrepreneur profile here as JSON, Java checks that every field is
 * within an allowed set of values and sensible ranges, and returns a
 * standardized JSON validation response.
 *
 * IMPORTANT: This service is OPTIONAL for the MVP to run. The Flask app
 * (app.py) tries to call it, but if it is not running, Flask falls back
 * to doing the same validation in Python so the website still works.
 * This keeps the demo reliable even if the jury forgets to start Java.
 *
 * This uses ONLY Java's built-in classes (com.sun.net.httpserver) —
 * no external frameworks or libraries are required.
 *
 * HOW TO COMPILE AND RUN (Windows, from the project's "java" folder):
 *     javac SchemeService.java
 *     java SchemeService
 *
 * The service will start on:
 *     http://127.0.0.1:8080/validate
 *
 * Health check:
 *     http://127.0.0.1:8080/status
 */

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SchemeService {

    private static final Set<String> VALID_GENDERS = new HashSet<>();
    private static final Set<String> VALID_CATEGORIES = new HashSet<>();
    private static final Set<String> VALID_BUSINESS_TYPES = new HashSet<>();
    private static final Set<String> VALID_STAGES = new HashSet<>();
    private static final Set<String> VALID_STATES = new HashSet<>();

    static {
        VALID_GENDERS.add("Female");
        VALID_GENDERS.add("Male");
        VALID_GENDERS.add("Other");

        VALID_CATEGORIES.add("SC");
        VALID_CATEGORIES.add("ST");
        VALID_CATEGORIES.add("OBC");
        VALID_CATEGORIES.add("General");

        VALID_BUSINESS_TYPES.add("Tailoring");
        VALID_BUSINESS_TYPES.add("Food Business");
        VALID_BUSINESS_TYPES.add("Retail");
        VALID_BUSINESS_TYPES.add("Manufacturing");
        VALID_BUSINESS_TYPES.add("Services");
        VALID_BUSINESS_TYPES.add("Agriculture");
        VALID_BUSINESS_TYPES.add("Handicraft");
        VALID_BUSINESS_TYPES.add("Technology");
        VALID_BUSINESS_TYPES.add("Other");

        VALID_STAGES.add("New Business");
        VALID_STAGES.add("Existing Business");
        VALID_STAGES.add("Expansion");

        VALID_STATES.add("Gujarat");
        VALID_STATES.add("Maharashtra");
        VALID_STATES.add("Rajasthan");
        VALID_STATES.add("Delhi");
        VALID_STATES.add("Uttar Pradesh");
        VALID_STATES.add("Madhya Pradesh");
        VALID_STATES.add("Karnataka");
        VALID_STATES.add("Tamil Nadu");
        VALID_STATES.add("West Bengal");
        VALID_STATES.add("Other");
    }

    public static void main(String[] args) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 8080), 0);
        server.createContext("/validate", new ValidateHandler());
        server.createContext("/status", new StatusHandler());
        server.setExecutor(null);
        server.start();
        System.out.println("SchemeMatch AI - Java validation service running at http://127.0.0.1:8080");
        System.out.println("Endpoints: POST /validate , GET /status");
    }

    /** Simple health/status endpoint. */
    static class StatusHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String json = "{\"status\":\"ok\",\"service\":\"SchemeService\"}";
            sendResponse(exchange, 200, json);
        }
    }

    /** Validates and normalizes an entrepreneur profile sent as JSON. */
    static class ValidateHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                sendResponse(exchange, 405, "{\"valid\":false,\"errors\":[\"Method not allowed\"]}");
                return;
            }

            String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);

            String gender = extractStringField(body, "gender");
            String category = extractStringField(body, "category");
            String businessType = extractStringField(body, "business_type");
            String businessStage = extractStringField(body, "business_stage");
            String state = extractStringField(body, "state");
            int age = extractIntField(body, "age");
            int income = extractIntField(body, "income");
            int funding = extractIntField(body, "funding_required");

            StringBuilder errors = new StringBuilder();
            boolean valid = true;

            if (!VALID_GENDERS.contains(gender)) {
                valid = false;
                appendError(errors, "Invalid gender value.");
            }
            if (!VALID_CATEGORIES.contains(category)) {
                valid = false;
                appendError(errors, "Invalid category value.");
            }
            if (!VALID_BUSINESS_TYPES.contains(businessType)) {
                valid = false;
                appendError(errors, "Invalid business type value.");
            }
            if (!VALID_STAGES.contains(businessStage)) {
                valid = false;
                appendError(errors, "Invalid business stage value.");
            }
            if (!VALID_STATES.contains(state)) {
                valid = false;
                appendError(errors, "Invalid state value.");
            }
            if (age < 18 || age > 100) {
                valid = false;
                appendError(errors, "Age must be between 18 and 100.");
            }
            if (income < 0) {
                valid = false;
                appendError(errors, "Income cannot be negative.");
            }
            if (funding < 0) {
                valid = false;
                appendError(errors, "Funding required cannot be negative.");
            }

            String json = "{\"valid\":" + valid + ",\"errors\":[" + errors + "]}";
            sendResponse(exchange, 200, json);
        }
    }

    private static void appendError(StringBuilder errors, String message) {
        if (errors.length() > 0) {
            errors.append(",");
        }
        errors.append("\"").append(message).append("\"");
    }

    /** Minimal hand-written JSON string field extractor (no external libraries). */
    private static String extractStringField(String json, String field) {
        Pattern pattern = Pattern.compile("\"" + field + "\"\\s*:\\s*\"([^\"]*)\"");
        Matcher matcher = pattern.matcher(json);
        return matcher.find() ? matcher.group(1) : "";
    }

    /** Minimal hand-written JSON integer field extractor (no external libraries). */
    private static int extractIntField(String json, String field) {
        Pattern pattern = Pattern.compile("\"" + field + "\"\\s*:\\s*(-?\\d+)");
        Matcher matcher = pattern.matcher(json);
        if (matcher.find()) {
            try {
                return Integer.parseInt(matcher.group(1));
            } catch (NumberFormatException e) {
                return 0;
            }
        }
        return 0;
    }

    private static void sendResponse(HttpExchange exchange, int statusCode, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.sendResponseHeaders(statusCode, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }
}