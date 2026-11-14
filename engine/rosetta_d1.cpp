// rosetta_d1: d1-2B resident on the IQ9 NPU via the ZETIC Ixian Hexagon SDK (Decision::systemOne).
// Same JSON Lines protocol as `zetic_d1_cli serve`:
//   in:  {"id":1,"state":"1. ...","questions":{"severity":{"type":"score","instructions":"...","criteria":["a","b"]}}}
//   out: {"id":1,"status":"Ok","answers":{"severity":{"type":"score","score":1,"legend":"b",...}},"passes":1,...}
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>
#include <zetic_decision.h>

using namespace zetic::ixian;
using json = nlohmann::ordered_json;

static void emit(const json& j) {
  std::cout << j.dump(-1, ' ', false, json::error_handler_t::replace) << '\n' << std::flush;
}

static const char* typeName(Question::Type t) {
  return t == Question::Type::Noul ? "noul" : t == Question::Type::Choice ? "choice" : "score";
}

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <d1 model dir>\n", argv[0]);
    return 2;
  }
  try {
    Decision d1 = Decision::fromPath(argv[1]);
    const ModelInfo& info = d1.info();
    emit({{"event", "ready"}, {"model", info.model_id}, {"target", info.target}, {"nsp_count", info.nsp_count},
          {"soc", info.soc}, {"sdk", info.sdk_version}, {"max_context", d1.capabilities().max_context}});
    std::string line;
    while (std::getline(std::cin, line)) {
      if (line.empty()) continue;
      json out = {{"id", nullptr}};
      try {
        json req = json::parse(line);
        out["id"] = req.value("id", json());
        State state = State::None();
        if (req.contains("state")) {
          const json& s = req["state"];
          if (s.is_string()) state = State::Text(s.get<std::string>());
          else if (!s.is_null()) state = State::Json(s.dump());
        }
        std::vector<std::pair<std::string, Question>> qs;
        const json& questions = req.at("questions");
        for (auto it = questions.begin(); it != questions.end(); ++it) {
          const json& q = it.value();
          const std::string type = q.value("type", std::string("noul"));
          const std::string instr = q.value("instructions", std::string());
          if (type == "noul") {
            qs.emplace_back(it.key(), Question::Noul(instr));
          } else if (type == "choice") {
            std::vector<std::pair<std::string, std::string>> crit;
            const json& c = q.at("criteria");
            for (auto ci = c.begin(); ci != c.end(); ++ci)
              crit.emplace_back(ci.key(), ci.value().is_string() ? ci.value().get<std::string>() : std::string());
            qs.emplace_back(it.key(), Question::Choice(instr, crit, q.value("multiple", false)));
          } else if (type == "score") {
            qs.emplace_back(it.key(), Question::Score(instr, q.at("criteria").get<std::vector<std::string>>()));
          } else {
            throw std::invalid_argument("unsupported question type: " + type);
          }
        }
        DecisionResult r = d1.systemOne(state, qs);
        out["status"] = statusName(r.status);
        if (r.status != Status::Ok) out["error"] = r.error;
        json answers = json::object();
        for (const auto& na : r.answers) {
          const Answer& a = na.second;
          answers[na.first] = {{"type", typeName(a.type)}, {"noul", a.noul}, {"choice", a.choice},
                               {"choices", a.choices}, {"confidence", a.confidence}, {"score", a.score},
                               {"legend", a.legend}, {"labels", a.labels}, {"probabilities", a.probs}};
        }
        out["answers"] = answers;
        out["passes"] = r.passes;
        out["input_tokens"] = r.input_tokens;
        out["timings"] = {{"encode_ms", r.timings.encode}, {"d1_ms", r.timings.prefill}, {"ttft_ms", r.timings.ttft}};
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
    fprintf(stderr, "rosetta_d1: load failed (%s): %s\n", statusName(e.status()), e.what());
    return 1;
  }
  return 0;
}
