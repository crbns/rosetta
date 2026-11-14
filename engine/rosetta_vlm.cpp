// rosetta_vlm: LFM3-VL-2B resident on the IQ9 Hexagon NPU via the ZETIC Ixian Hexagon SDK.
// Protocol: JSON Lines on stdin -> JSON Lines on stdout (same pattern as zetic_d1_cli serve). Logs go to stderr.
//   usage: rosetta_vlm <model dir> [target ("" = v73, or v73-1nsp)] [max_context]
//   in:  {"id":1,"system":"...","prompt":"...","images":["/dev/shm/rosetta/scan-1.png"],"max_tokens":768,"temperature":0,"think":false}
//   out: {"id":1,"status":"Ok","text":"...","finish":"Stop","usage":{...},"timings":{...}}
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>
#include <zetic_llm.h>

using namespace zetic::ixian;
using json = nlohmann::ordered_json;

static void emit(const json& j) {
  std::cout << j.dump(-1, ' ', false, json::error_handler_t::replace) << '\n' << std::flush;
}

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <model dir> [target] [max_context]\n", argv[0]);
    return 2;
  }
  LLM::Options opt;
  opt.target = argc > 2 ? argv[2] : "";
  opt.max_context = argc > 3 ? std::stoi(argv[3]) : 4096;
  opt.max_new_tokens = 768;
  try {
    LLM llm = LLM::fromPath(argv[1], opt);
    const ModelInfo& info = llm.info();
    emit({{"event", "ready"}, {"model", info.model_id}, {"target", info.target}, {"nsp_count", info.nsp_count},
          {"soc", info.soc}, {"sdk", info.sdk_version}, {"package", info.package_version},
          {"max_context", llm.capabilities().max_context}});
    std::string line;
    while (std::getline(std::cin, line)) {
      if (line.empty()) continue;
      json out = {{"id", nullptr}};
      try {
        json req = json::parse(line);
        out["id"] = req.value("id", json());
        std::vector<Part> parts;
        if (req.contains("images"))
          for (const auto& p : req["images"]) parts.push_back(Part::Img(Image::fromFile(p.get<std::string>())));
        parts.push_back(Part::Text(req.value("prompt", std::string())));
        std::vector<Message> msgs;
        if (req.contains("system")) msgs.push_back(Message::System(req["system"].get<std::string>()));
        msgs.push_back(Message::User(std::move(parts)));

        GenerationConfig cfg;
        cfg.max_tokens = req.value("max_tokens", 768);
        cfg.temperature = req.value("temperature", 0.0f);
        cfg.enable_thinking = req.value("think", false);

        Response r = llm.chat(msgs, cfg);
        out["status"] = statusName(r.status);
        if (r.status != Status::Ok) out["error"] = r.error;
        out["text"] = r.text;
        out["reasoning"] = r.reasoning_content;
        out["finish"] = finishReasonName(r.finish_reason);
        out["usage"] = {{"prompt_rows", r.usage.prompt_rows}, {"cached_rows", r.usage.cached_rows},
                        {"completion_tokens", r.usage.completion_tokens}};
        out["timings"] = {{"ttft_ms", r.timings.ttft}, {"encode_ms", r.timings.encode},
                          {"prefill_ms", r.timings.prefill}, {"decode_ms", r.timings.decode},
                          {"tokens_per_second", r.timings.tokens_per_second}};
        if (r.status == Status::DeviceError) llm.reload();
        else if (r.status == Status::ContextExceeded) llm.reset();
      } catch (const Error& e) {
        out["status"] = statusName(e.status());
        out["error"] = e.what();
      } catch (const std::exception& e) {
        out["status"] = "InvalidArgument";
        out["error"] = e.what();
      }
      emit(out);
    }
  } catch (const Error& e) {
    fprintf(stderr, "rosetta_vlm: load failed (%s): %s\n", statusName(e.status()), e.what());
    return 1;
  }
  return 0;
}
