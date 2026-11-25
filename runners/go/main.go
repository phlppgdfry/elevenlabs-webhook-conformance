// Usage: go run . vectors.json  (go.mod replaces the SDK with the checkout under test)
package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/elevenlabs/elevenlabs-go/webhooks"
)

type vector struct {
	ID     string `json:"id"`
	Header string `json:"header"`
	Body   string `json:"body"`
	Secret string `json:"secret"`
}

func main() {
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	var file struct{ Vectors []vector }
	if err := json.Unmarshal(raw, &file); err != nil {
		panic(err)
	}
	results := map[string]map[string]any{}
	for _, v := range file.Vectors {
		func() {
			defer func() {
				if r := recover(); r != nil {
					results[v.ID] = map[string]any{"ok": false, "error": "panic", "message": fmt.Sprint(r)}
				}
			}()
			if _, err := webhooks.ConstructEvent([]byte(v.Body), v.Header, v.Secret); err != nil {
				results[v.ID] = map[string]any{"ok": false, "error": fmt.Sprintf("%T", err), "message": err.Error()}
				return
			}
			results[v.ID] = map[string]any{"ok": true}
		}()
	}
	out, _ := json.Marshal(results)
	os.Stdout.Write(out)
}
