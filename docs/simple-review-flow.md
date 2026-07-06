# 简化人工审核流程

目标：你只负责**看和选**，不用手动改数据、不用运行命令、不用提交。

## 1. 打开审核清单

```text
docs/review/review-queue.md
```

或者让 Hermes 重新生成：

```bash
python3 scripts/generate_review_queue.py --limit 20
```

## 2. 你只需要按编号回复

示例：

```text
1 降级 watch：有趣但不是核心 coding agent 能力。
2 保留 try-now：写作 humanizer skill 有明确用途。
3 保留 try-now：Claude Skills 生态样本，值得优先观察。
4 改为 reference：更像中文本地化资料。
5 移除 rejected：不是 AI Coding Agent 核心生态。
```

## 3. Hermes 负责后续全部操作

收到你的选择后，Hermes 必须：

1. 修改 `data/curated-projects.yaml`。
2. 必要时修改 `data/rejected-projects.yaml`。
3. 同步修改 `data/projects.yaml`。
4. 运行：

```bash
python3 scripts/update_tracker.py --skip-collect
```

5. 验证：

```text
https://coding.lzpgood.online/
```

6. 提交并推送。

## 4. 可选动作

| 动作 | 含义 |
|---|---|
| 保留 try-now | 继续优先推荐 |
| 降级 watch | 保留但只观察 |
| 改为 reference | 作为资料/教程/参考 |
| 改为 experimental | 标为实验性 |
| 移除 rejected | 移出 curated，放入 rejected |
| 改分类 | 指定新 category |
| 改关联工具 | 指定新 target_tools |

## 5. 你最短可以这样回复

```text
1 watch
2 keep
3 keep
4 reference
5 reject
```

Hermes 会结合当前记录解释并执行。
