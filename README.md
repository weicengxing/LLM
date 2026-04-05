# Mini LLM From Scratch

这是一个从零开始搭建的最小大语言模型项目，目标不是复刻工业级模型，而是提供一个结构清晰、能训练、能生成文本、便于继续扩展的教学级代码库。

## 项目目标

- 从零实现一个简化版 GPT 风格语言模型
- 文件职责清晰，便于阅读和二次开发
- 支持训练、保存检查点、加载模型并生成文本
- 不依赖外部数据集，开箱即用

## 目录结构

```text
.
├── README.md                  # 项目说明和使用方式
├── requirements.txt           # Python 依赖
├── train.py                   # 训练入口
├── generate.py                # 生成入口
├── data/
│   └── sample_corpus.txt      # 默认训练语料
└── src/
    └── mini_llm/
        ├── __init__.py        # 包导出
        ├── checkpoint.py      # 模型保存/加载
        ├── config.py          # 训练与模型配置
        ├── data.py            # 数据集构建与批次采样
        ├── generation.py      # 文本采样生成
        ├── model.py           # GPT 风格 Transformer 模型
        ├── tokenizer.py       # 字符级 tokenizer
        └── trainer.py         # 训练循环
```

## 快速开始

1. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. 训练模型

```bash
python train.py
```

3. 使用训练后的模型生成文本

```bash
python generate.py --prompt "大语言模型"
```

## 当前实现说明

- 使用字符级 tokenizer，简单直接，便于理解
- 模型是简化版 Decoder-Only Transformer
- 默认数据集很小，仅用于验证流程是否跑通
- 如果你要进一步做成更像“真正的大模型”，可以继续扩展：
  - 改成 BPE tokenizer
  - 引入更大语料
  - 支持多卡训练
  - 增加学习率调度、混合精度、评估集
  - 支持更成熟的 checkpoint 管理

## 默认输出

训练完成后会在 `artifacts/` 目录下生成：

- `model.pt`：模型权重与配置
- `tokenizer.json`：字符表

## 适合的下一步

如果你愿意，我下一步可以继续帮你：

- 接着把它升级成 `BPE tokenizer + 更规范配置文件`
- 加上 `Web UI`
- 改成 `对话式 SFT` 训练结构
- 接入你自己的文本语料
