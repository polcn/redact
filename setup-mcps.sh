#!/bin/bash
# MCP Setup Script - Ensures AWS MCPs are always available

echo "Setting up AWS MCPs for persistence..."

# Create Claude config directory
mkdir -p ~/.claude

# Find latest MCP server binaries
AWS_DOC_MCP=$(find ~/.cache/uv -name "awslabs.aws-documentation-mcp-server" -type f -executable | head -1)
AWS_CDK_MCP=$(find ~/.cache/uv -name "awslabs.cdk-mcp-server" -type f -executable | head -1)
AWS_CORE_MCP=$(find ~/.cache/uv -name "awslabs.core-mcp-server" -type f -executable | head -1)
AWS_SERVERLESS_MCP=$(find ~/.cache/uv -name "awslabs.aws-serverless-mcp-server" -type f -executable | head -1)

# Create MCP settings file
cat > ~/.claude/mcp_settings.json << EOF
{
  "mcpServers": {
    "aws-documentation": {
      "command": "$AWS_DOC_MCP",
      "args": [],
      "env": {}
    },
    "aws-cdk": {
      "command": "$AWS_CDK_MCP",
      "args": [],
      "env": {}
    },
    "aws-core": {
      "command": "$AWS_CORE_MCP",
      "args": [],
      "env": {}
    },
    "aws-serverless": {
      "command": "$AWS_SERVERLESS_MCP",
      "args": [],
      "env": {}
    }
  }
}
EOF

echo "MCP configuration created at ~/.claude/mcp_settings.json"
echo "MCPs will persist across Claude sessions"
echo "Available MCPs:"
echo "  - aws-documentation: AWS service documentation"
echo "  - aws-cdk: AWS CDK utilities"
echo "  - aws-core: Core AWS operations"
echo "  - aws-serverless: Serverless framework support"