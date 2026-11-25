// Usage: dotnet run -c Release -- vectors.json
using System.Text.Json;
using System.Text.Json.Nodes;
using ElevenLabs.Webhooks;

var file = JsonNode.Parse(File.ReadAllText(args[0]))!;
var results = new JsonObject();
foreach (var v in file["vectors"]!.AsArray())
{
    var id = (string)v!["id"]!;
    try
    {
        WebhookVerifier.ConstructEvent((string)v["body"]!, (string)v["header"]!, (string)v["secret"]!);
        results[id] = new JsonObject { ["ok"] = true };
    }
    catch (Exception e)
    {
        results[id] = new JsonObject { ["ok"] = false, ["error"] = e.GetType().Name, ["message"] = e.Message };
    }
}
Console.Out.Write(results.ToJsonString());
