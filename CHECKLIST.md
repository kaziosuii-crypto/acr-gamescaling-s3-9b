# CHECKLIST · GameScaling-9B-S3 推理镜像

## A. 仓库内容（构建源）
- [x] `Dockerfile` — server-only，三层（依赖 / 服务资产 / 权重最后）
- [x] `entrypoint.sh` — `vllm serve` + `--host 0.0.0.0`
- [x] `download_weights.py` — 构建期拉权重
- [x] `verify_weights.py` — 构建期完整性闸门
- [x] `smoke_test.py` — 镜像内自检
- [x] `requirements-runtime.txt`
- [x] `.dockerignore`（排除 `caller-reference/`）
- [x] `docker-compose.yml`
- [x] `README.md`
- [x] `caller-reference/` — 官方 client/prompts/examples/scripts 逐字副本（**不进镜像**）

## B. 构建期校验点（由 verify_weights.py 自动执行，失败即中断构建）
- [x] 9 个必需文件齐全（config / safetensors / chat_template / tokenizer / generation / preprocessor / processor / video_preprocessor）
- [x] `config.model_type == "qwen3_5"`
- [x] `architectures` 含 `Qwen3_5ForConditionalGeneration`
- [x] `model.safetensors` 字节数 == 18,819,722,392
- [x] safetensors 头可解析（张量数 / dtype）
- [x] 可选 `VERIFY_SHA256=1`：全量 sha256 == `18afe037afcf175abd061193ab98d0d46f90224ffc28c083fe2a12ed366d7d50`

## C. ACR 侧（需在控制台完成）
- [ ] 绑定 Git 代码源（GitHub 需一次 OAuth 授权；或用户自备可写 GitLab 仓库）
- [ ] 创建仓库 `gamescaling-s3-9b`（命名空间 `peiyang`，地域 华东2（上海），私有）
- [ ] 关联代码源：分支 `main`，上下文目录 `/`，Dockerfile 文件名 `Dockerfile`，镜像版本 `latest`
- [ ] 勾选 **海外机器构建**（需访问 huggingface.co 拉 18.8 GB 权重）
- [ ] 触发构建并盯日志直到成功（用户实测同类构建可跑 2 小时）
- [ ] 构建成功后确认镜像版本 `latest` 存在

## D. 推理机验收
- [ ] `docker login` 到 `crpi-1jy2xtmkqkdwjcgv.cn-shanghai.personal.cr.aliyuncs.com`
- [ ] `docker pull .../peiyang/gamescaling-s3-9b:latest` 成功
- [ ] `docker run --gpus all --shm-size 16g -p 8000:8000` 容器保持 running
- [ ] `curl -s http://127.0.0.1:8000/v1/models` 返回 `id: "gamescaling"`
- [ ] `docker exec gamescaling python3 /opt/GameScaling/smoke_test.py` 通过
- [ ] 官方 `run_example.py`（在 `caller-reference/examples/`）用 Doom 帧跑出 `<|action_start|>...<|action_end|>` 且 `parsed and not truncated`

## E. 前提确认
- [x] 镜像为 linux/amd64
- [x] 运行期不联网下载权重（权重已在镜像内）
- [x] 目标机需要 NVIDIA 驱动 + nvidia-container-toolkit
- [x] 显存说明：官方未声明最低；建议单卡 ≥24 GB，推荐 40 GB+（本地实证 4090 48 GB）
- [x] 镜像体积约 28 GB

## F. 交付
- [ ] 打包 zip（保留目录结构 + 校验清单）
