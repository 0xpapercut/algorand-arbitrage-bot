class TransactionError(Exception): ...
class PoolTransactionError(TransactionError): ...
class NoSecretFileFoundError(Exception): ...
class PoolNotFoundError(Exception): ...
class NotOptedIntoAssetError(Exception): ...
class ArbitrageOperationError(Exception): ...
class PoolValueError(ValueError): ...
class LowAmountInError(ValueError): ...
class PoolFetchError(Exception): ...