# Python 虚拟环境说明

## 为什么需要虚拟环境？

虚拟环境（venv）可以隔离项目的 Python 依赖，避免不同项目之间的包版本冲突。

## 创建虚拟环境

```bash
cd backend

# 创建虚拟环境（环境名为 venv）
python -m venv venv
```

## 激活虚拟环境

**Windows（命令提示符）：**
```cmd
venv\Scripts\activate
```

**Windows（PowerShell）：**
```powershell
venv\Scripts\Activate.ps1
```

> 如果 PowerShell 提示"无法加载文件"，先执行：
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

**macOS / Linux：**
```bash
source venv/bin/activate
```

激活成功后，终端提示符前会出现 `(venv)` 标记。

## 安装依赖

```bash
# 确保虚拟环境已激活（看到 (venv) 标记）
pip install -r requirements.txt
```

## 退出虚拟环境

```bash
deactivate
```

## 删除重建

如果虚拟环境出现问题，可以删除后重建：

```bash
# Windows
rmdir /s venv

# macOS/Linux
rm -rf venv

# 重建
python -m venv venv
pip install -r requirements.txt
```

## 相关文件

- `.gitignore` 已忽略 `venv/` 目录，不会提交到 Git
- `requirements.txt` 记录所有依赖及版本
