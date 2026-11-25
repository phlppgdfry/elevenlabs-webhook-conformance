// Compiled with javac -sourcepath <java checkout>/src/main/java, so only the classes the verifier needs are built.
import com.elevenlabs.api.webhooks.WebhookVerifier;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.File;

public class Runner {
  public static void main(String[] args) throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    JsonNode file = mapper.readTree(new File(args[0]));
    ObjectNode results = mapper.createObjectNode();
    for (JsonNode v : file.get("vectors")) {
      ObjectNode r = mapper.createObjectNode();
      try {
        WebhookVerifier.constructEvent(v.get("body").asText(), v.get("header").asText(), v.get("secret").asText());
        r.put("ok", true);
      } catch (Exception e) {
        r.put("ok", false);
        r.put("error", e.getClass().getSimpleName());
        r.put("message", e.getMessage());
      }
      results.set(v.get("id").asText(), r);
    }
    System.out.print(mapper.writeValueAsString(results));
  }
}
