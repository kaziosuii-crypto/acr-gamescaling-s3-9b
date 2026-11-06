# GameScaling-9B-S3 · 开箱即用推理镜像

一个 **Linux x86_64** 的模型推理容器镜像：权重（18.8 GB BF16）+ vLLM 0.17 推理底座 + 运行依赖全部内置。
推理机 `docker pull` 之后直接 `docker run` 即可对外提供 OpenAI 兼容的 `gamescaling` 端点，**运行期不联网下载任何东西**。

- 模型：`THUSI-Lab/GameScaling-9B-S3`
  - revision `673fcdc5b442467bbf73102f38defb2ba93d5c9b`
  - `model.safetensors` = 18,819,722,392 B（sha256 `18afe037afcf175abd061193ab98d0d46f90224ffc28c083fe2a12ed366d7d50`）
  - 架构 `Qwen3_5ForConditionalGeneration`（基座 Qwen3.5-9B，架构 `qwen3_5`），上下文 32k，视觉输入 ≤ 8 图/请求
- 基础镜像：`vllm/vllm-openai:v0.17.0@sha256:14ea8b431aaaf75eb873c46c8ebfbad2b4b0790d30c66126d789d8cb9bd0aab9`
- 镜像体积：约 28 GB（基础镜像 9.27 GB + 权重 18.8 GB）
- 仓库地址：`crpi-1jy2xtmkqkdwjcgv.cn-shanghai.personal.cr.aliyuncs.com/peiyang/gamescaling-s3-9b`

---

## 1. 推理机前提（必须先满足）

| 项 | 要求 |
|---|---|
| GPU | NVIDIA，**单卡显存 ≥ 24 GB**，推荐 40 GB+（本地实测 4090 48 GB 可跑；官方未声明最低显存） |
| 驱动 | NVIDIA 驱动 + `nvidia-container-toolkit`（否则容器看不到 GPU） |
| 磁盘 | 拉镜像需 ≥ 30 GB 可用空间 |
| 系统 | x86_64 Linux；镜像与宿主需同为 x86_64 |

> 权重是 bf16 单文件，约 18.8 GB；再加 KV cache、视觉编码与运行时开销，实际显存需求高于 18.8 GB。

## 2. 拉起

```bash
docker login --username=逍遥天下独行客 crpi-1jy2xtmkqkdwjcgv.cn-shanghai.personal.cr.aliyuncs.com
# 密码 = 开通服务时设置的访问凭证密码（ACR 控制台「访问凭证」页可改）

docker pull crpi-1jy2xtmkqkdwjcgv.cn-shanghai.personal.cr.aliyuncs.com/peiyang/gamescaling-s3-9b:latest

docker run -d --name gamescaling \
  --gpus all \
  --shm-size 16g \
  -p 8000:8000 \
  crpi-1jy2xtmkqkdwjcgv.cn-shanghai.personal.cr.aliyuncs.com/peiyang/gamescaling-s3-9b:latest
```

也可直接用仓库内的 `docker-compose.yml`：

```bash
docker compose up -d
```

首次启动需要把 18.8 GB 权重从磁盘读进显存并做 kernel 编译，**健康检查最长 900 s 才开始判定**（Dockerfile `HEALTHCHECK --start-period=900s`）。用下面命令判断是否就绪：

```bash
curl -s http://127.0.0.1:8000/v1/models
# 期望：{"object":"list","data":[{"id":"gamescaling", ...}]}
```

容器内自检：

```bash
docker exec -it gamescaling python3 /opt/GameScaling/smoke_test.py
```

## 3. 调用协议（与官方 `gamescaling` 客户端完全一致）

请求 `POST /v1/chat/completions`，**三个参数一个都不能少**：

```jsonc
{
  "model": "gamescaling",
  "messages": [
    {"role": "system", "content": "<官方 build_system_prompt 生成的 system prompt>"},
    {"role": "user", "content": "current game screen"},
    {"role": "assistant", "content": "<think>\n\n</think>\n\n"}   // assistant prefill
  ],
  "temperature": 1.0,
  "skip_special_tokens": false,     // 必须 false，否则动作标签被吞
  "continue_final_message": true,   // 与 prefill 配合
  "add_generation_prompt": false
}
```

用户消息里的图片用 data URL：

```json
{"role": "user", "content": [
  {"type": "text", "text": "current game screen"},
  {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,...."}}
]}
```

响应文本形如：

```
<think>...</think><|action_start|>X Y Z ; k1 k2 k3 ; k4 k5 ; k6 ; k7 ; k8 ; k9 k10<|action_end|>
```

`<|action_start|>` 与 `<|action_end|>` 之间是 6 步 / 200 ms 的动作块（`X Y Z` 为鼠标位移，`.` 表示按住，`k` 为按键）。

调用侧的完整实现见仓库里的 `caller-reference/`（官方 `gamescaling` 包逐字副本，含 `parse_action`、`build_request`、`build_system_prompt`）——**它属于调用方，不在镜像内**。

## 4. 运行时可调参数

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `PORT` | 8000 | 服务端口 |
| `TENSOR_PARALLEL_SIZE` | 1 | 多卡张量并行 |
| `GPU_MEM_UTIL` | 0.85 | vLLM 显存占用比例 |
| `MAX_MODEL_LEN` | 32768 | 上下文长度 |
| `VLLM_API_KEY` | 空 | 设置后启用 `--api-key`，调用需带 Bearer |

## 5. 目录结构

```
.
├── Dockerfile                 # 三层：依赖 / 服务资产 / 权重（最后、最重）
├── entrypoint.sh              # vllm serve，补 --host 0.0.0.0
├── download_weights.py        # 构建期拉权重（snapshot_download + hf_transfer）
├── verify_weights.py          # 构建期完整性闸门（必需文件/大小/sha256）
├── smoke_test.py              # 镜像内自检
├── requirements-runtime.txt
├── .dockerignore
├── docker-compose.yml
├── README.md
├── CHECKLIST.md
└── caller-reference/          # 官方客户端逐字副本（不进镜像）
    ├── client/{__init__,action,keymaps,policy,prompt}.py
    ├── prompts/{system_prompt_template,example_doom_battle1}.txt
    ├── examples/{run_example.py,doom_battle1.jpg,doom_battle1_action.txt}
    └── scripts/serve_vllm.sh
```

## 6. 构建说明（本仓库用于 ACR 云端构建）

- ACR「云端构建」必须绑定一个 Git 代码源；构建规则：类型 `Branch`/分支 `main`、构建上下文目录 `/`、Dockerfile 文件名 `Dockerfile`、镜像版本 `latest`。
- **必须勾选「海外机器构建」**：构建机要能访问 `huggingface.co` 才能把 18.8 GB 权重拉下来。
- 权重层放在最后，改依赖/脚本不需要重新下载 18.8 GB。
- 构建期耗时主要在权重下载；`HF_HOME=/tmp/hf-cache` 且同层删除，避免镜像里出现第二份 18.8 GB。
