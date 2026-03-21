using System.Threading;

namespace Common.Mock;

public abstract class AmbientScopeBase<T> : IDisposable where T : AmbientScopeBase<T>
{
    private static readonly AsyncLocal<T?> _current = new();

    private readonly T? _previousScope;
    private bool _disposed;

    public static T? Current => _current.Value;

    protected AmbientScopeBase()
    {
        _previousScope = _current.Value;
    }

    protected static T StartNew(T instance)
    {
        _current.Value = instance;
        return instance;
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            _disposed = true;
            _current.Value = _previousScope;
        }
    }
}
