using Microsoft.AspNetCore.Mvc;

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
}
