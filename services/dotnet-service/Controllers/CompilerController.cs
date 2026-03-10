using Microsoft.AspNetCore.Mvc;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using System.Reflection;

namespace DotNetService.Controllers;

[ApiController]
[Route("api/[controller]")]
public class CompilerController : ControllerBase
{
    private readonly ILogger<CompilerController> _logger;

    public CompilerController(ILogger<CompilerController> logger)
    {
        _logger = logger;
    }

    [HttpPost("compile")]
    public async Task<IResult> CompileCodeAsync([FromBody] CompileRequest request, CancellationToken ct)
    {
        _logger.LogInformation("Received compile request for code length: {Length}", request.SourceCode.Length);
        
        var result = await CompileWithRoslynAsync(request.SourceCode, ct);
        
        return result.IsSuccess 
            ? Results.Ok(new { message = "Compilation successful", result.Value }) 
            : Results.BadRequest(new { error = result.Error, code = result.ErrorCode });
    }

    private Task<Result<string>> CompileWithRoslynAsync(string code, CancellationToken ct)
    {
        var syntaxTree = CSharpSyntaxTree.ParseText(code);
        var references = new[]
        {
            MetadataReference.CreateFromFile(typeof(object).GetTypeInfo().Assembly.Location),
            MetadataReference.CreateFromFile(typeof(Console).GetTypeInfo().Assembly.Location)
        };

        var compilation = CSharpCompilation.Create("DynamicUOM")
            .WithOptions(new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary))
            .AddReferences(references)
            .AddSyntaxTrees(syntaxTree);

        using var ms = new MemoryStream();
        var emitResult = compilation.Emit(ms, cancellationToken: ct);

        if (!emitResult.Success)
        {
            var failures = emitResult.Diagnostics.Where(diagnostic => 
                diagnostic.IsWarningAsError || 
                diagnostic.Severity == DiagnosticSeverity.Error);
                
            var errors = string.Join("\n", failures.Select(f => f.Id + ": " + f.GetMessage()));
            return Task.FromResult(Result<string>.Failure(errors, "COMPILATION_ERROR"));
        }

        return Task.FromResult(Result<string>.Success("Assembly generated successfully."));
    }
}

public record CompileRequest(string SourceCode);

// Generic Result Pattern
public class Result<T>
{
    public bool IsSuccess { get; }
    public T? Value { get; }
    public string? Error { get; }
    public string? ErrorCode { get; }

    private Result(bool isSuccess, T? value, string? error, string? errorCode)
    {
        IsSuccess = isSuccess;
        Value = value;
        Error = error;
        ErrorCode = errorCode;
    }

    public static Result<T> Success(T value) => new(true, value, null, null);
    public static Result<T> Failure(string error, string? code = null) => new(false, default, error, code);
}
