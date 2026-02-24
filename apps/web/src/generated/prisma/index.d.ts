
/**
 * Client
**/

import * as runtime from './runtime/client.js';
import $Types = runtime.Types // general types
import $Public = runtime.Types.Public
import $Utils = runtime.Types.Utils
import $Extensions = runtime.Types.Extensions
import $Result = runtime.Types.Result

export type PrismaPromise<T> = $Public.PrismaPromise<T>


/**
 * Model User
 * 
 */
export type User = $Result.DefaultSelection<Prisma.$UserPayload>
/**
 * Model Account
 * 
 */
export type Account = $Result.DefaultSelection<Prisma.$AccountPayload>
/**
 * Model Session
 * 
 */
export type Session = $Result.DefaultSelection<Prisma.$SessionPayload>
/**
 * Model VerificationToken
 * 
 */
export type VerificationToken = $Result.DefaultSelection<Prisma.$VerificationTokenPayload>
/**
 * Model Sport
 * 
 */
export type Sport = $Result.DefaultSelection<Prisma.$SportPayload>
/**
 * Model Team
 * 
 */
export type Team = $Result.DefaultSelection<Prisma.$TeamPayload>
/**
 * Model Game
 * 
 */
export type Game = $Result.DefaultSelection<Prisma.$GamePayload>
/**
 * Model MarketSnapshot
 * 
 */
export type MarketSnapshot = $Result.DefaultSelection<Prisma.$MarketSnapshotPayload>
/**
 * Model BookLine
 * 
 */
export type BookLine = $Result.DefaultSelection<Prisma.$BookLinePayload>
/**
 * Model ModelProjection
 * 
 */
export type ModelProjection = $Result.DefaultSelection<Prisma.$ModelProjectionPayload>
/**
 * Model Writeup
 * 
 */
export type Writeup = $Result.DefaultSelection<Prisma.$WriteupPayload>
/**
 * Model Injury
 * 
 */
export type Injury = $Result.DefaultSelection<Prisma.$InjuryPayload>
/**
 * Model TeamProfileWeekly
 * 
 */
export type TeamProfileWeekly = $Result.DefaultSelection<Prisma.$TeamProfileWeeklyPayload>

/**
 * Enums
 */
export namespace $Enums {
  export const UserRole: {
  USER: 'USER',
  PRO: 'PRO',
  ADMIN: 'ADMIN'
};

export type UserRole = (typeof UserRole)[keyof typeof UserRole]


export const SubscriptionStatus: {
  ACTIVE: 'ACTIVE',
  CANCELLED: 'CANCELLED',
  EXPIRED: 'EXPIRED',
  TRIAL: 'TRIAL'
};

export type SubscriptionStatus = (typeof SubscriptionStatus)[keyof typeof SubscriptionStatus]


export const EditorStatus: {
  DRAFT: 'DRAFT',
  REVIEWED: 'REVIEWED',
  PUBLISHED: 'PUBLISHED'
};

export type EditorStatus = (typeof EditorStatus)[keyof typeof EditorStatus]


export const InjuryStatus: {
  OUT: 'OUT',
  DOUBTFUL: 'DOUBTFUL',
  QUESTIONABLE: 'QUESTIONABLE',
  PROBABLE: 'PROBABLE'
};

export type InjuryStatus = (typeof InjuryStatus)[keyof typeof InjuryStatus]


export const InjuryImpact: {
  STAR: 'STAR',
  ROTATION: 'ROTATION',
  MINOR: 'MINOR'
};

export type InjuryImpact = (typeof InjuryImpact)[keyof typeof InjuryImpact]

}

export type UserRole = $Enums.UserRole

export const UserRole: typeof $Enums.UserRole

export type SubscriptionStatus = $Enums.SubscriptionStatus

export const SubscriptionStatus: typeof $Enums.SubscriptionStatus

export type EditorStatus = $Enums.EditorStatus

export const EditorStatus: typeof $Enums.EditorStatus

export type InjuryStatus = $Enums.InjuryStatus

export const InjuryStatus: typeof $Enums.InjuryStatus

export type InjuryImpact = $Enums.InjuryImpact

export const InjuryImpact: typeof $Enums.InjuryImpact

/**
 * ##  Prisma Client ʲˢ
 *
 * Type-safe database client for TypeScript & Node.js
 * @example
 * ```
 * const prisma = new PrismaClient()
 * // Fetch zero or more Users
 * const users = await prisma.user.findMany()
 * ```
 *
 *
 * Read more in our [docs](https://pris.ly/d/client).
 */
export class PrismaClient<
  ClientOptions extends Prisma.PrismaClientOptions = Prisma.PrismaClientOptions,
  const U = 'log' extends keyof ClientOptions ? ClientOptions['log'] extends Array<Prisma.LogLevel | Prisma.LogDefinition> ? Prisma.GetEvents<ClientOptions['log']> : never : never,
  ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs
> {
  [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['other'] }

    /**
   * ##  Prisma Client ʲˢ
   *
   * Type-safe database client for TypeScript & Node.js
   * @example
   * ```
   * const prisma = new PrismaClient()
   * // Fetch zero or more Users
   * const users = await prisma.user.findMany()
   * ```
   *
   *
   * Read more in our [docs](https://pris.ly/d/client).
   */

  constructor(optionsArg ?: Prisma.Subset<ClientOptions, Prisma.PrismaClientOptions>);
  $on<V extends U>(eventType: V, callback: (event: V extends 'query' ? Prisma.QueryEvent : Prisma.LogEvent) => void): PrismaClient;

  /**
   * Connect with the database
   */
  $connect(): $Utils.JsPromise<void>;

  /**
   * Disconnect from the database
   */
  $disconnect(): $Utils.JsPromise<void>;

/**
   * Executes a prepared raw query and returns the number of affected rows.
   * @example
   * ```
   * const result = await prisma.$executeRaw`UPDATE User SET cool = ${true} WHERE email = ${'user@email.com'};`
   * ```
   *
   * Read more in our [docs](https://pris.ly/d/raw-queries).
   */
  $executeRaw<T = unknown>(query: TemplateStringsArray | Prisma.Sql, ...values: any[]): Prisma.PrismaPromise<number>;

  /**
   * Executes a raw query and returns the number of affected rows.
   * Susceptible to SQL injections, see documentation.
   * @example
   * ```
   * const result = await prisma.$executeRawUnsafe('UPDATE User SET cool = $1 WHERE email = $2 ;', true, 'user@email.com')
   * ```
   *
   * Read more in our [docs](https://pris.ly/d/raw-queries).
   */
  $executeRawUnsafe<T = unknown>(query: string, ...values: any[]): Prisma.PrismaPromise<number>;

  /**
   * Performs a prepared raw query and returns the `SELECT` data.
   * @example
   * ```
   * const result = await prisma.$queryRaw`SELECT * FROM User WHERE id = ${1} OR email = ${'user@email.com'};`
   * ```
   *
   * Read more in our [docs](https://pris.ly/d/raw-queries).
   */
  $queryRaw<T = unknown>(query: TemplateStringsArray | Prisma.Sql, ...values: any[]): Prisma.PrismaPromise<T>;

  /**
   * Performs a raw query and returns the `SELECT` data.
   * Susceptible to SQL injections, see documentation.
   * @example
   * ```
   * const result = await prisma.$queryRawUnsafe('SELECT * FROM User WHERE id = $1 OR email = $2;', 1, 'user@email.com')
   * ```
   *
   * Read more in our [docs](https://pris.ly/d/raw-queries).
   */
  $queryRawUnsafe<T = unknown>(query: string, ...values: any[]): Prisma.PrismaPromise<T>;


  /**
   * Allows the running of a sequence of read/write operations that are guaranteed to either succeed or fail as a whole.
   * @example
   * ```
   * const [george, bob, alice] = await prisma.$transaction([
   *   prisma.user.create({ data: { name: 'George' } }),
   *   prisma.user.create({ data: { name: 'Bob' } }),
   *   prisma.user.create({ data: { name: 'Alice' } }),
   * ])
   * ```
   * 
   * Read more in our [docs](https://www.prisma.io/docs/concepts/components/prisma-client/transactions).
   */
  $transaction<P extends Prisma.PrismaPromise<any>[]>(arg: [...P], options?: { isolationLevel?: Prisma.TransactionIsolationLevel }): $Utils.JsPromise<runtime.Types.Utils.UnwrapTuple<P>>

  $transaction<R>(fn: (prisma: Omit<PrismaClient, runtime.ITXClientDenyList>) => $Utils.JsPromise<R>, options?: { maxWait?: number, timeout?: number, isolationLevel?: Prisma.TransactionIsolationLevel }): $Utils.JsPromise<R>

  $extends: $Extensions.ExtendsHook<"extends", Prisma.TypeMapCb<ClientOptions>, ExtArgs, $Utils.Call<Prisma.TypeMapCb<ClientOptions>, {
    extArgs: ExtArgs
  }>>

      /**
   * `prisma.user`: Exposes CRUD operations for the **User** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Users
    * const users = await prisma.user.findMany()
    * ```
    */
  get user(): Prisma.UserDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.account`: Exposes CRUD operations for the **Account** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Accounts
    * const accounts = await prisma.account.findMany()
    * ```
    */
  get account(): Prisma.AccountDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.session`: Exposes CRUD operations for the **Session** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Sessions
    * const sessions = await prisma.session.findMany()
    * ```
    */
  get session(): Prisma.SessionDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.verificationToken`: Exposes CRUD operations for the **VerificationToken** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more VerificationTokens
    * const verificationTokens = await prisma.verificationToken.findMany()
    * ```
    */
  get verificationToken(): Prisma.VerificationTokenDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.sport`: Exposes CRUD operations for the **Sport** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Sports
    * const sports = await prisma.sport.findMany()
    * ```
    */
  get sport(): Prisma.SportDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.team`: Exposes CRUD operations for the **Team** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Teams
    * const teams = await prisma.team.findMany()
    * ```
    */
  get team(): Prisma.TeamDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.game`: Exposes CRUD operations for the **Game** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Games
    * const games = await prisma.game.findMany()
    * ```
    */
  get game(): Prisma.GameDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.marketSnapshot`: Exposes CRUD operations for the **MarketSnapshot** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more MarketSnapshots
    * const marketSnapshots = await prisma.marketSnapshot.findMany()
    * ```
    */
  get marketSnapshot(): Prisma.MarketSnapshotDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.bookLine`: Exposes CRUD operations for the **BookLine** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more BookLines
    * const bookLines = await prisma.bookLine.findMany()
    * ```
    */
  get bookLine(): Prisma.BookLineDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.modelProjection`: Exposes CRUD operations for the **ModelProjection** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more ModelProjections
    * const modelProjections = await prisma.modelProjection.findMany()
    * ```
    */
  get modelProjection(): Prisma.ModelProjectionDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.writeup`: Exposes CRUD operations for the **Writeup** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Writeups
    * const writeups = await prisma.writeup.findMany()
    * ```
    */
  get writeup(): Prisma.WriteupDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.injury`: Exposes CRUD operations for the **Injury** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Injuries
    * const injuries = await prisma.injury.findMany()
    * ```
    */
  get injury(): Prisma.InjuryDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.teamProfileWeekly`: Exposes CRUD operations for the **TeamProfileWeekly** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more TeamProfileWeeklies
    * const teamProfileWeeklies = await prisma.teamProfileWeekly.findMany()
    * ```
    */
  get teamProfileWeekly(): Prisma.TeamProfileWeeklyDelegate<ExtArgs, ClientOptions>;
}

export namespace Prisma {
  export import DMMF = runtime.DMMF

  export type PrismaPromise<T> = $Public.PrismaPromise<T>

  /**
   * Validator
   */
  export import validator = runtime.Public.validator

  /**
   * Prisma Errors
   */
  export import PrismaClientKnownRequestError = runtime.PrismaClientKnownRequestError
  export import PrismaClientUnknownRequestError = runtime.PrismaClientUnknownRequestError
  export import PrismaClientRustPanicError = runtime.PrismaClientRustPanicError
  export import PrismaClientInitializationError = runtime.PrismaClientInitializationError
  export import PrismaClientValidationError = runtime.PrismaClientValidationError

  /**
   * Re-export of sql-template-tag
   */
  export import sql = runtime.sqltag
  export import empty = runtime.empty
  export import join = runtime.join
  export import raw = runtime.raw
  export import Sql = runtime.Sql



  /**
   * Decimal.js
   */
  export import Decimal = runtime.Decimal

  export type DecimalJsLike = runtime.DecimalJsLike

  /**
  * Extensions
  */
  export import Extension = $Extensions.UserArgs
  export import getExtensionContext = runtime.Extensions.getExtensionContext
  export import Args = $Public.Args
  export import Payload = $Public.Payload
  export import Result = $Public.Result
  export import Exact = $Public.Exact

  /**
   * Prisma Client JS version: 7.4.0
   * Query Engine version: ab56fe763f921d033a6c195e7ddeb3e255bdbb57
   */
  export type PrismaVersion = {
    client: string
    engine: string
  }

  export const prismaVersion: PrismaVersion

  /**
   * Utility Types
   */


  export import Bytes = runtime.Bytes
  export import JsonObject = runtime.JsonObject
  export import JsonArray = runtime.JsonArray
  export import JsonValue = runtime.JsonValue
  export import InputJsonObject = runtime.InputJsonObject
  export import InputJsonArray = runtime.InputJsonArray
  export import InputJsonValue = runtime.InputJsonValue

  /**
   * Types of the values used to represent different kinds of `null` values when working with JSON fields.
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  namespace NullTypes {
    /**
    * Type of `Prisma.DbNull`.
    *
    * You cannot use other instances of this class. Please use the `Prisma.DbNull` value.
    *
    * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
    */
    class DbNull {
      private DbNull: never
      private constructor()
    }

    /**
    * Type of `Prisma.JsonNull`.
    *
    * You cannot use other instances of this class. Please use the `Prisma.JsonNull` value.
    *
    * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
    */
    class JsonNull {
      private JsonNull: never
      private constructor()
    }

    /**
    * Type of `Prisma.AnyNull`.
    *
    * You cannot use other instances of this class. Please use the `Prisma.AnyNull` value.
    *
    * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
    */
    class AnyNull {
      private AnyNull: never
      private constructor()
    }
  }

  /**
   * Helper for filtering JSON entries that have `null` on the database (empty on the db)
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  export const DbNull: NullTypes.DbNull

  /**
   * Helper for filtering JSON entries that have JSON `null` values (not empty on the db)
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  export const JsonNull: NullTypes.JsonNull

  /**
   * Helper for filtering JSON entries that are `Prisma.DbNull` or `Prisma.JsonNull`
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  export const AnyNull: NullTypes.AnyNull

  type SelectAndInclude = {
    select: any
    include: any
  }

  type SelectAndOmit = {
    select: any
    omit: any
  }

  /**
   * Get the type of the value, that the Promise holds.
   */
  export type PromiseType<T extends PromiseLike<any>> = T extends PromiseLike<infer U> ? U : T;

  /**
   * Get the return type of a function which returns a Promise.
   */
  export type PromiseReturnType<T extends (...args: any) => $Utils.JsPromise<any>> = PromiseType<ReturnType<T>>

  /**
   * From T, pick a set of properties whose keys are in the union K
   */
  type Prisma__Pick<T, K extends keyof T> = {
      [P in K]: T[P];
  };


  export type Enumerable<T> = T | Array<T>;

  export type RequiredKeys<T> = {
    [K in keyof T]-?: {} extends Prisma__Pick<T, K> ? never : K
  }[keyof T]

  export type TruthyKeys<T> = keyof {
    [K in keyof T as T[K] extends false | undefined | null ? never : K]: K
  }

  export type TrueKeys<T> = TruthyKeys<Prisma__Pick<T, RequiredKeys<T>>>

  /**
   * Subset
   * @desc From `T` pick properties that exist in `U`. Simple version of Intersection
   */
  export type Subset<T, U> = {
    [key in keyof T]: key extends keyof U ? T[key] : never;
  };

  /**
   * SelectSubset
   * @desc From `T` pick properties that exist in `U`. Simple version of Intersection.
   * Additionally, it validates, if both select and include are present. If the case, it errors.
   */
  export type SelectSubset<T, U> = {
    [key in keyof T]: key extends keyof U ? T[key] : never
  } &
    (T extends SelectAndInclude
      ? 'Please either choose `select` or `include`.'
      : T extends SelectAndOmit
        ? 'Please either choose `select` or `omit`.'
        : {})

  /**
   * Subset + Intersection
   * @desc From `T` pick properties that exist in `U` and intersect `K`
   */
  export type SubsetIntersection<T, U, K> = {
    [key in keyof T]: key extends keyof U ? T[key] : never
  } &
    K

  type Without<T, U> = { [P in Exclude<keyof T, keyof U>]?: never };

  /**
   * XOR is needed to have a real mutually exclusive union type
   * https://stackoverflow.com/questions/42123407/does-typescript-support-mutually-exclusive-types
   */
  type XOR<T, U> =
    T extends object ?
    U extends object ?
      (Without<T, U> & U) | (Without<U, T> & T)
    : U : T


  /**
   * Is T a Record?
   */
  type IsObject<T extends any> = T extends Array<any>
  ? False
  : T extends Date
  ? False
  : T extends Uint8Array
  ? False
  : T extends BigInt
  ? False
  : T extends object
  ? True
  : False


  /**
   * If it's T[], return T
   */
  export type UnEnumerate<T extends unknown> = T extends Array<infer U> ? U : T

  /**
   * From ts-toolbelt
   */

  type __Either<O extends object, K extends Key> = Omit<O, K> &
    {
      // Merge all but K
      [P in K]: Prisma__Pick<O, P & keyof O> // With K possibilities
    }[K]

  type EitherStrict<O extends object, K extends Key> = Strict<__Either<O, K>>

  type EitherLoose<O extends object, K extends Key> = ComputeRaw<__Either<O, K>>

  type _Either<
    O extends object,
    K extends Key,
    strict extends Boolean
  > = {
    1: EitherStrict<O, K>
    0: EitherLoose<O, K>
  }[strict]

  type Either<
    O extends object,
    K extends Key,
    strict extends Boolean = 1
  > = O extends unknown ? _Either<O, K, strict> : never

  export type Union = any

  type PatchUndefined<O extends object, O1 extends object> = {
    [K in keyof O]: O[K] extends undefined ? At<O1, K> : O[K]
  } & {}

  /** Helper Types for "Merge" **/
  export type IntersectOf<U extends Union> = (
    U extends unknown ? (k: U) => void : never
  ) extends (k: infer I) => void
    ? I
    : never

  export type Overwrite<O extends object, O1 extends object> = {
      [K in keyof O]: K extends keyof O1 ? O1[K] : O[K];
  } & {};

  type _Merge<U extends object> = IntersectOf<Overwrite<U, {
      [K in keyof U]-?: At<U, K>;
  }>>;

  type Key = string | number | symbol;
  type AtBasic<O extends object, K extends Key> = K extends keyof O ? O[K] : never;
  type AtStrict<O extends object, K extends Key> = O[K & keyof O];
  type AtLoose<O extends object, K extends Key> = O extends unknown ? AtStrict<O, K> : never;
  export type At<O extends object, K extends Key, strict extends Boolean = 1> = {
      1: AtStrict<O, K>;
      0: AtLoose<O, K>;
  }[strict];

  export type ComputeRaw<A extends any> = A extends Function ? A : {
    [K in keyof A]: A[K];
  } & {};

  export type OptionalFlat<O> = {
    [K in keyof O]?: O[K];
  } & {};

  type _Record<K extends keyof any, T> = {
    [P in K]: T;
  };

  // cause typescript not to expand types and preserve names
  type NoExpand<T> = T extends unknown ? T : never;

  // this type assumes the passed object is entirely optional
  type AtLeast<O extends object, K extends string> = NoExpand<
    O extends unknown
    ? | (K extends keyof O ? { [P in K]: O[P] } & O : O)
      | {[P in keyof O as P extends K ? P : never]-?: O[P]} & O
    : never>;

  type _Strict<U, _U = U> = U extends unknown ? U & OptionalFlat<_Record<Exclude<Keys<_U>, keyof U>, never>> : never;

  export type Strict<U extends object> = ComputeRaw<_Strict<U>>;
  /** End Helper Types for "Merge" **/

  export type Merge<U extends object> = ComputeRaw<_Merge<Strict<U>>>;

  /**
  A [[Boolean]]
  */
  export type Boolean = True | False

  // /**
  // 1
  // */
  export type True = 1

  /**
  0
  */
  export type False = 0

  export type Not<B extends Boolean> = {
    0: 1
    1: 0
  }[B]

  export type Extends<A1 extends any, A2 extends any> = [A1] extends [never]
    ? 0 // anything `never` is false
    : A1 extends A2
    ? 1
    : 0

  export type Has<U extends Union, U1 extends Union> = Not<
    Extends<Exclude<U1, U>, U1>
  >

  export type Or<B1 extends Boolean, B2 extends Boolean> = {
    0: {
      0: 0
      1: 1
    }
    1: {
      0: 1
      1: 1
    }
  }[B1][B2]

  export type Keys<U extends Union> = U extends unknown ? keyof U : never

  type Cast<A, B> = A extends B ? A : B;

  export const type: unique symbol;



  /**
   * Used by group by
   */

  export type GetScalarType<T, O> = O extends object ? {
    [P in keyof T]: P extends keyof O
      ? O[P]
      : never
  } : never

  type FieldPaths<
    T,
    U = Omit<T, '_avg' | '_sum' | '_count' | '_min' | '_max'>
  > = IsObject<T> extends True ? U : T

  type GetHavingFields<T> = {
    [K in keyof T]: Or<
      Or<Extends<'OR', K>, Extends<'AND', K>>,
      Extends<'NOT', K>
    > extends True
      ? // infer is only needed to not hit TS limit
        // based on the brilliant idea of Pierre-Antoine Mills
        // https://github.com/microsoft/TypeScript/issues/30188#issuecomment-478938437
        T[K] extends infer TK
        ? GetHavingFields<UnEnumerate<TK> extends object ? Merge<UnEnumerate<TK>> : never>
        : never
      : {} extends FieldPaths<T[K]>
      ? never
      : K
  }[keyof T]

  /**
   * Convert tuple to union
   */
  type _TupleToUnion<T> = T extends (infer E)[] ? E : never
  type TupleToUnion<K extends readonly any[]> = _TupleToUnion<K>
  type MaybeTupleToUnion<T> = T extends any[] ? TupleToUnion<T> : T

  /**
   * Like `Pick`, but additionally can also accept an array of keys
   */
  type PickEnumerable<T, K extends Enumerable<keyof T> | keyof T> = Prisma__Pick<T, MaybeTupleToUnion<K>>

  /**
   * Exclude all keys with underscores
   */
  type ExcludeUnderscoreKeys<T extends string> = T extends `_${string}` ? never : T


  export type FieldRef<Model, FieldType> = runtime.FieldRef<Model, FieldType>

  type FieldRefInputType<Model, FieldType> = Model extends never ? never : FieldRef<Model, FieldType>


  export const ModelName: {
    User: 'User',
    Account: 'Account',
    Session: 'Session',
    VerificationToken: 'VerificationToken',
    Sport: 'Sport',
    Team: 'Team',
    Game: 'Game',
    MarketSnapshot: 'MarketSnapshot',
    BookLine: 'BookLine',
    ModelProjection: 'ModelProjection',
    Writeup: 'Writeup',
    Injury: 'Injury',
    TeamProfileWeekly: 'TeamProfileWeekly'
  };

  export type ModelName = (typeof ModelName)[keyof typeof ModelName]



  interface TypeMapCb<ClientOptions = {}> extends $Utils.Fn<{extArgs: $Extensions.InternalArgs }, $Utils.Record<string, any>> {
    returns: Prisma.TypeMap<this['params']['extArgs'], ClientOptions extends { omit: infer OmitOptions } ? OmitOptions : {}>
  }

  export type TypeMap<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> = {
    globalOmitOptions: {
      omit: GlobalOmitOptions
    }
    meta: {
      modelProps: "user" | "account" | "session" | "verificationToken" | "sport" | "team" | "game" | "marketSnapshot" | "bookLine" | "modelProjection" | "writeup" | "injury" | "teamProfileWeekly"
      txIsolationLevel: Prisma.TransactionIsolationLevel
    }
    model: {
      User: {
        payload: Prisma.$UserPayload<ExtArgs>
        fields: Prisma.UserFieldRefs
        operations: {
          findUnique: {
            args: Prisma.UserFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.UserFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          findFirst: {
            args: Prisma.UserFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.UserFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          findMany: {
            args: Prisma.UserFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>[]
          }
          create: {
            args: Prisma.UserCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          createMany: {
            args: Prisma.UserCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.UserCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>[]
          }
          delete: {
            args: Prisma.UserDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          update: {
            args: Prisma.UserUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          deleteMany: {
            args: Prisma.UserDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.UserUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.UserUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>[]
          }
          upsert: {
            args: Prisma.UserUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$UserPayload>
          }
          aggregate: {
            args: Prisma.UserAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateUser>
          }
          groupBy: {
            args: Prisma.UserGroupByArgs<ExtArgs>
            result: $Utils.Optional<UserGroupByOutputType>[]
          }
          count: {
            args: Prisma.UserCountArgs<ExtArgs>
            result: $Utils.Optional<UserCountAggregateOutputType> | number
          }
        }
      }
      Account: {
        payload: Prisma.$AccountPayload<ExtArgs>
        fields: Prisma.AccountFieldRefs
        operations: {
          findUnique: {
            args: Prisma.AccountFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.AccountFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload>
          }
          findFirst: {
            args: Prisma.AccountFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.AccountFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload>
          }
          findMany: {
            args: Prisma.AccountFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload>[]
          }
          create: {
            args: Prisma.AccountCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload>
          }
          createMany: {
            args: Prisma.AccountCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.AccountCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload>[]
          }
          delete: {
            args: Prisma.AccountDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload>
          }
          update: {
            args: Prisma.AccountUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload>
          }
          deleteMany: {
            args: Prisma.AccountDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.AccountUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.AccountUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload>[]
          }
          upsert: {
            args: Prisma.AccountUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AccountPayload>
          }
          aggregate: {
            args: Prisma.AccountAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateAccount>
          }
          groupBy: {
            args: Prisma.AccountGroupByArgs<ExtArgs>
            result: $Utils.Optional<AccountGroupByOutputType>[]
          }
          count: {
            args: Prisma.AccountCountArgs<ExtArgs>
            result: $Utils.Optional<AccountCountAggregateOutputType> | number
          }
        }
      }
      Session: {
        payload: Prisma.$SessionPayload<ExtArgs>
        fields: Prisma.SessionFieldRefs
        operations: {
          findUnique: {
            args: Prisma.SessionFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.SessionFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          findFirst: {
            args: Prisma.SessionFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.SessionFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          findMany: {
            args: Prisma.SessionFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>[]
          }
          create: {
            args: Prisma.SessionCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          createMany: {
            args: Prisma.SessionCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.SessionCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>[]
          }
          delete: {
            args: Prisma.SessionDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          update: {
            args: Prisma.SessionUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          deleteMany: {
            args: Prisma.SessionDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.SessionUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.SessionUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>[]
          }
          upsert: {
            args: Prisma.SessionUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          aggregate: {
            args: Prisma.SessionAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateSession>
          }
          groupBy: {
            args: Prisma.SessionGroupByArgs<ExtArgs>
            result: $Utils.Optional<SessionGroupByOutputType>[]
          }
          count: {
            args: Prisma.SessionCountArgs<ExtArgs>
            result: $Utils.Optional<SessionCountAggregateOutputType> | number
          }
        }
      }
      VerificationToken: {
        payload: Prisma.$VerificationTokenPayload<ExtArgs>
        fields: Prisma.VerificationTokenFieldRefs
        operations: {
          findUnique: {
            args: Prisma.VerificationTokenFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.VerificationTokenFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload>
          }
          findFirst: {
            args: Prisma.VerificationTokenFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.VerificationTokenFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload>
          }
          findMany: {
            args: Prisma.VerificationTokenFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload>[]
          }
          create: {
            args: Prisma.VerificationTokenCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload>
          }
          createMany: {
            args: Prisma.VerificationTokenCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.VerificationTokenCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload>[]
          }
          delete: {
            args: Prisma.VerificationTokenDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload>
          }
          update: {
            args: Prisma.VerificationTokenUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload>
          }
          deleteMany: {
            args: Prisma.VerificationTokenDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.VerificationTokenUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.VerificationTokenUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload>[]
          }
          upsert: {
            args: Prisma.VerificationTokenUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$VerificationTokenPayload>
          }
          aggregate: {
            args: Prisma.VerificationTokenAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateVerificationToken>
          }
          groupBy: {
            args: Prisma.VerificationTokenGroupByArgs<ExtArgs>
            result: $Utils.Optional<VerificationTokenGroupByOutputType>[]
          }
          count: {
            args: Prisma.VerificationTokenCountArgs<ExtArgs>
            result: $Utils.Optional<VerificationTokenCountAggregateOutputType> | number
          }
        }
      }
      Sport: {
        payload: Prisma.$SportPayload<ExtArgs>
        fields: Prisma.SportFieldRefs
        operations: {
          findUnique: {
            args: Prisma.SportFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.SportFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload>
          }
          findFirst: {
            args: Prisma.SportFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.SportFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload>
          }
          findMany: {
            args: Prisma.SportFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload>[]
          }
          create: {
            args: Prisma.SportCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload>
          }
          createMany: {
            args: Prisma.SportCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.SportCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload>[]
          }
          delete: {
            args: Prisma.SportDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload>
          }
          update: {
            args: Prisma.SportUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload>
          }
          deleteMany: {
            args: Prisma.SportDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.SportUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.SportUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload>[]
          }
          upsert: {
            args: Prisma.SportUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SportPayload>
          }
          aggregate: {
            args: Prisma.SportAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateSport>
          }
          groupBy: {
            args: Prisma.SportGroupByArgs<ExtArgs>
            result: $Utils.Optional<SportGroupByOutputType>[]
          }
          count: {
            args: Prisma.SportCountArgs<ExtArgs>
            result: $Utils.Optional<SportCountAggregateOutputType> | number
          }
        }
      }
      Team: {
        payload: Prisma.$TeamPayload<ExtArgs>
        fields: Prisma.TeamFieldRefs
        operations: {
          findUnique: {
            args: Prisma.TeamFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.TeamFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload>
          }
          findFirst: {
            args: Prisma.TeamFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.TeamFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload>
          }
          findMany: {
            args: Prisma.TeamFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload>[]
          }
          create: {
            args: Prisma.TeamCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload>
          }
          createMany: {
            args: Prisma.TeamCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.TeamCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload>[]
          }
          delete: {
            args: Prisma.TeamDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload>
          }
          update: {
            args: Prisma.TeamUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload>
          }
          deleteMany: {
            args: Prisma.TeamDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.TeamUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.TeamUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload>[]
          }
          upsert: {
            args: Prisma.TeamUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamPayload>
          }
          aggregate: {
            args: Prisma.TeamAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateTeam>
          }
          groupBy: {
            args: Prisma.TeamGroupByArgs<ExtArgs>
            result: $Utils.Optional<TeamGroupByOutputType>[]
          }
          count: {
            args: Prisma.TeamCountArgs<ExtArgs>
            result: $Utils.Optional<TeamCountAggregateOutputType> | number
          }
        }
      }
      Game: {
        payload: Prisma.$GamePayload<ExtArgs>
        fields: Prisma.GameFieldRefs
        operations: {
          findUnique: {
            args: Prisma.GameFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.GameFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload>
          }
          findFirst: {
            args: Prisma.GameFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.GameFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload>
          }
          findMany: {
            args: Prisma.GameFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload>[]
          }
          create: {
            args: Prisma.GameCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload>
          }
          createMany: {
            args: Prisma.GameCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.GameCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload>[]
          }
          delete: {
            args: Prisma.GameDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload>
          }
          update: {
            args: Prisma.GameUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload>
          }
          deleteMany: {
            args: Prisma.GameDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.GameUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.GameUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload>[]
          }
          upsert: {
            args: Prisma.GameUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$GamePayload>
          }
          aggregate: {
            args: Prisma.GameAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateGame>
          }
          groupBy: {
            args: Prisma.GameGroupByArgs<ExtArgs>
            result: $Utils.Optional<GameGroupByOutputType>[]
          }
          count: {
            args: Prisma.GameCountArgs<ExtArgs>
            result: $Utils.Optional<GameCountAggregateOutputType> | number
          }
        }
      }
      MarketSnapshot: {
        payload: Prisma.$MarketSnapshotPayload<ExtArgs>
        fields: Prisma.MarketSnapshotFieldRefs
        operations: {
          findUnique: {
            args: Prisma.MarketSnapshotFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.MarketSnapshotFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload>
          }
          findFirst: {
            args: Prisma.MarketSnapshotFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.MarketSnapshotFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload>
          }
          findMany: {
            args: Prisma.MarketSnapshotFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload>[]
          }
          create: {
            args: Prisma.MarketSnapshotCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload>
          }
          createMany: {
            args: Prisma.MarketSnapshotCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.MarketSnapshotCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload>[]
          }
          delete: {
            args: Prisma.MarketSnapshotDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload>
          }
          update: {
            args: Prisma.MarketSnapshotUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload>
          }
          deleteMany: {
            args: Prisma.MarketSnapshotDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.MarketSnapshotUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.MarketSnapshotUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload>[]
          }
          upsert: {
            args: Prisma.MarketSnapshotUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$MarketSnapshotPayload>
          }
          aggregate: {
            args: Prisma.MarketSnapshotAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateMarketSnapshot>
          }
          groupBy: {
            args: Prisma.MarketSnapshotGroupByArgs<ExtArgs>
            result: $Utils.Optional<MarketSnapshotGroupByOutputType>[]
          }
          count: {
            args: Prisma.MarketSnapshotCountArgs<ExtArgs>
            result: $Utils.Optional<MarketSnapshotCountAggregateOutputType> | number
          }
        }
      }
      BookLine: {
        payload: Prisma.$BookLinePayload<ExtArgs>
        fields: Prisma.BookLineFieldRefs
        operations: {
          findUnique: {
            args: Prisma.BookLineFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.BookLineFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload>
          }
          findFirst: {
            args: Prisma.BookLineFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.BookLineFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload>
          }
          findMany: {
            args: Prisma.BookLineFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload>[]
          }
          create: {
            args: Prisma.BookLineCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload>
          }
          createMany: {
            args: Prisma.BookLineCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.BookLineCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload>[]
          }
          delete: {
            args: Prisma.BookLineDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload>
          }
          update: {
            args: Prisma.BookLineUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload>
          }
          deleteMany: {
            args: Prisma.BookLineDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.BookLineUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.BookLineUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload>[]
          }
          upsert: {
            args: Prisma.BookLineUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$BookLinePayload>
          }
          aggregate: {
            args: Prisma.BookLineAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateBookLine>
          }
          groupBy: {
            args: Prisma.BookLineGroupByArgs<ExtArgs>
            result: $Utils.Optional<BookLineGroupByOutputType>[]
          }
          count: {
            args: Prisma.BookLineCountArgs<ExtArgs>
            result: $Utils.Optional<BookLineCountAggregateOutputType> | number
          }
        }
      }
      ModelProjection: {
        payload: Prisma.$ModelProjectionPayload<ExtArgs>
        fields: Prisma.ModelProjectionFieldRefs
        operations: {
          findUnique: {
            args: Prisma.ModelProjectionFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.ModelProjectionFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload>
          }
          findFirst: {
            args: Prisma.ModelProjectionFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.ModelProjectionFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload>
          }
          findMany: {
            args: Prisma.ModelProjectionFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload>[]
          }
          create: {
            args: Prisma.ModelProjectionCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload>
          }
          createMany: {
            args: Prisma.ModelProjectionCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.ModelProjectionCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload>[]
          }
          delete: {
            args: Prisma.ModelProjectionDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload>
          }
          update: {
            args: Prisma.ModelProjectionUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload>
          }
          deleteMany: {
            args: Prisma.ModelProjectionDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.ModelProjectionUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.ModelProjectionUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload>[]
          }
          upsert: {
            args: Prisma.ModelProjectionUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ModelProjectionPayload>
          }
          aggregate: {
            args: Prisma.ModelProjectionAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateModelProjection>
          }
          groupBy: {
            args: Prisma.ModelProjectionGroupByArgs<ExtArgs>
            result: $Utils.Optional<ModelProjectionGroupByOutputType>[]
          }
          count: {
            args: Prisma.ModelProjectionCountArgs<ExtArgs>
            result: $Utils.Optional<ModelProjectionCountAggregateOutputType> | number
          }
        }
      }
      Writeup: {
        payload: Prisma.$WriteupPayload<ExtArgs>
        fields: Prisma.WriteupFieldRefs
        operations: {
          findUnique: {
            args: Prisma.WriteupFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.WriteupFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload>
          }
          findFirst: {
            args: Prisma.WriteupFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.WriteupFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload>
          }
          findMany: {
            args: Prisma.WriteupFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload>[]
          }
          create: {
            args: Prisma.WriteupCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload>
          }
          createMany: {
            args: Prisma.WriteupCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.WriteupCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload>[]
          }
          delete: {
            args: Prisma.WriteupDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload>
          }
          update: {
            args: Prisma.WriteupUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload>
          }
          deleteMany: {
            args: Prisma.WriteupDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.WriteupUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.WriteupUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload>[]
          }
          upsert: {
            args: Prisma.WriteupUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$WriteupPayload>
          }
          aggregate: {
            args: Prisma.WriteupAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateWriteup>
          }
          groupBy: {
            args: Prisma.WriteupGroupByArgs<ExtArgs>
            result: $Utils.Optional<WriteupGroupByOutputType>[]
          }
          count: {
            args: Prisma.WriteupCountArgs<ExtArgs>
            result: $Utils.Optional<WriteupCountAggregateOutputType> | number
          }
        }
      }
      Injury: {
        payload: Prisma.$InjuryPayload<ExtArgs>
        fields: Prisma.InjuryFieldRefs
        operations: {
          findUnique: {
            args: Prisma.InjuryFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.InjuryFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload>
          }
          findFirst: {
            args: Prisma.InjuryFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.InjuryFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload>
          }
          findMany: {
            args: Prisma.InjuryFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload>[]
          }
          create: {
            args: Prisma.InjuryCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload>
          }
          createMany: {
            args: Prisma.InjuryCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.InjuryCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload>[]
          }
          delete: {
            args: Prisma.InjuryDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload>
          }
          update: {
            args: Prisma.InjuryUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload>
          }
          deleteMany: {
            args: Prisma.InjuryDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.InjuryUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.InjuryUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload>[]
          }
          upsert: {
            args: Prisma.InjuryUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$InjuryPayload>
          }
          aggregate: {
            args: Prisma.InjuryAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateInjury>
          }
          groupBy: {
            args: Prisma.InjuryGroupByArgs<ExtArgs>
            result: $Utils.Optional<InjuryGroupByOutputType>[]
          }
          count: {
            args: Prisma.InjuryCountArgs<ExtArgs>
            result: $Utils.Optional<InjuryCountAggregateOutputType> | number
          }
        }
      }
      TeamProfileWeekly: {
        payload: Prisma.$TeamProfileWeeklyPayload<ExtArgs>
        fields: Prisma.TeamProfileWeeklyFieldRefs
        operations: {
          findUnique: {
            args: Prisma.TeamProfileWeeklyFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.TeamProfileWeeklyFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload>
          }
          findFirst: {
            args: Prisma.TeamProfileWeeklyFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.TeamProfileWeeklyFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload>
          }
          findMany: {
            args: Prisma.TeamProfileWeeklyFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload>[]
          }
          create: {
            args: Prisma.TeamProfileWeeklyCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload>
          }
          createMany: {
            args: Prisma.TeamProfileWeeklyCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.TeamProfileWeeklyCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload>[]
          }
          delete: {
            args: Prisma.TeamProfileWeeklyDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload>
          }
          update: {
            args: Prisma.TeamProfileWeeklyUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload>
          }
          deleteMany: {
            args: Prisma.TeamProfileWeeklyDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.TeamProfileWeeklyUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.TeamProfileWeeklyUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload>[]
          }
          upsert: {
            args: Prisma.TeamProfileWeeklyUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TeamProfileWeeklyPayload>
          }
          aggregate: {
            args: Prisma.TeamProfileWeeklyAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateTeamProfileWeekly>
          }
          groupBy: {
            args: Prisma.TeamProfileWeeklyGroupByArgs<ExtArgs>
            result: $Utils.Optional<TeamProfileWeeklyGroupByOutputType>[]
          }
          count: {
            args: Prisma.TeamProfileWeeklyCountArgs<ExtArgs>
            result: $Utils.Optional<TeamProfileWeeklyCountAggregateOutputType> | number
          }
        }
      }
    }
  } & {
    other: {
      payload: any
      operations: {
        $executeRaw: {
          args: [query: TemplateStringsArray | Prisma.Sql, ...values: any[]],
          result: any
        }
        $executeRawUnsafe: {
          args: [query: string, ...values: any[]],
          result: any
        }
        $queryRaw: {
          args: [query: TemplateStringsArray | Prisma.Sql, ...values: any[]],
          result: any
        }
        $queryRawUnsafe: {
          args: [query: string, ...values: any[]],
          result: any
        }
      }
    }
  }
  export const defineExtension: $Extensions.ExtendsHook<"define", Prisma.TypeMapCb, $Extensions.DefaultArgs>
  export type DefaultPrismaClient = PrismaClient
  export type ErrorFormat = 'pretty' | 'colorless' | 'minimal'
  export interface PrismaClientOptions {
    /**
     * @default "colorless"
     */
    errorFormat?: ErrorFormat
    /**
     * @example
     * ```
     * // Shorthand for `emit: 'stdout'`
     * log: ['query', 'info', 'warn', 'error']
     * 
     * // Emit as events only
     * log: [
     *   { emit: 'event', level: 'query' },
     *   { emit: 'event', level: 'info' },
     *   { emit: 'event', level: 'warn' }
     *   { emit: 'event', level: 'error' }
     * ]
     * 
     * / Emit as events and log to stdout
     * og: [
     *  { emit: 'stdout', level: 'query' },
     *  { emit: 'stdout', level: 'info' },
     *  { emit: 'stdout', level: 'warn' }
     *  { emit: 'stdout', level: 'error' }
     * 
     * ```
     * Read more in our [docs](https://pris.ly/d/logging).
     */
    log?: (LogLevel | LogDefinition)[]
    /**
     * The default values for transactionOptions
     * maxWait ?= 2000
     * timeout ?= 5000
     */
    transactionOptions?: {
      maxWait?: number
      timeout?: number
      isolationLevel?: Prisma.TransactionIsolationLevel
    }
    /**
     * Instance of a Driver Adapter, e.g., like one provided by `@prisma/adapter-planetscale`
     */
    adapter?: runtime.SqlDriverAdapterFactory
    /**
     * Prisma Accelerate URL allowing the client to connect through Accelerate instead of a direct database.
     */
    accelerateUrl?: string
    /**
     * Global configuration for omitting model fields by default.
     * 
     * @example
     * ```
     * const prisma = new PrismaClient({
     *   omit: {
     *     user: {
     *       password: true
     *     }
     *   }
     * })
     * ```
     */
    omit?: Prisma.GlobalOmitConfig
    /**
     * SQL commenter plugins that add metadata to SQL queries as comments.
     * Comments follow the sqlcommenter format: https://google.github.io/sqlcommenter/
     * 
     * @example
     * ```
     * const prisma = new PrismaClient({
     *   adapter,
     *   comments: [
     *     traceContext(),
     *     queryInsights(),
     *   ],
     * })
     * ```
     */
    comments?: runtime.SqlCommenterPlugin[]
  }
  export type GlobalOmitConfig = {
    user?: UserOmit
    account?: AccountOmit
    session?: SessionOmit
    verificationToken?: VerificationTokenOmit
    sport?: SportOmit
    team?: TeamOmit
    game?: GameOmit
    marketSnapshot?: MarketSnapshotOmit
    bookLine?: BookLineOmit
    modelProjection?: ModelProjectionOmit
    writeup?: WriteupOmit
    injury?: InjuryOmit
    teamProfileWeekly?: TeamProfileWeeklyOmit
  }

  /* Types for Logging */
  export type LogLevel = 'info' | 'query' | 'warn' | 'error'
  export type LogDefinition = {
    level: LogLevel
    emit: 'stdout' | 'event'
  }

  export type CheckIsLogLevel<T> = T extends LogLevel ? T : never;

  export type GetLogType<T> = CheckIsLogLevel<
    T extends LogDefinition ? T['level'] : T
  >;

  export type GetEvents<T extends any[]> = T extends Array<LogLevel | LogDefinition>
    ? GetLogType<T[number]>
    : never;

  export type QueryEvent = {
    timestamp: Date
    query: string
    params: string
    duration: number
    target: string
  }

  export type LogEvent = {
    timestamp: Date
    message: string
    target: string
  }
  /* End Types for Logging */


  export type PrismaAction =
    | 'findUnique'
    | 'findUniqueOrThrow'
    | 'findMany'
    | 'findFirst'
    | 'findFirstOrThrow'
    | 'create'
    | 'createMany'
    | 'createManyAndReturn'
    | 'update'
    | 'updateMany'
    | 'updateManyAndReturn'
    | 'upsert'
    | 'delete'
    | 'deleteMany'
    | 'executeRaw'
    | 'queryRaw'
    | 'aggregate'
    | 'count'
    | 'runCommandRaw'
    | 'findRaw'
    | 'groupBy'

  // tested in getLogLevel.test.ts
  export function getLogLevel(log: Array<LogLevel | LogDefinition>): LogLevel | undefined;

  /**
   * `PrismaClient` proxy available in interactive transactions.
   */
  export type TransactionClient = Omit<Prisma.DefaultPrismaClient, runtime.ITXClientDenyList>

  export type Datasource = {
    url?: string
  }

  /**
   * Count Types
   */


  /**
   * Count Type UserCountOutputType
   */

  export type UserCountOutputType = {
    accounts: number
    sessions: number
  }

  export type UserCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    accounts?: boolean | UserCountOutputTypeCountAccountsArgs
    sessions?: boolean | UserCountOutputTypeCountSessionsArgs
  }

  // Custom InputTypes
  /**
   * UserCountOutputType without action
   */
  export type UserCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the UserCountOutputType
     */
    select?: UserCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * UserCountOutputType without action
   */
  export type UserCountOutputTypeCountAccountsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: AccountWhereInput
  }

  /**
   * UserCountOutputType without action
   */
  export type UserCountOutputTypeCountSessionsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: SessionWhereInput
  }


  /**
   * Count Type SportCountOutputType
   */

  export type SportCountOutputType = {
    teams: number
    games: number
  }

  export type SportCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    teams?: boolean | SportCountOutputTypeCountTeamsArgs
    games?: boolean | SportCountOutputTypeCountGamesArgs
  }

  // Custom InputTypes
  /**
   * SportCountOutputType without action
   */
  export type SportCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the SportCountOutputType
     */
    select?: SportCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * SportCountOutputType without action
   */
  export type SportCountOutputTypeCountTeamsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TeamWhereInput
  }

  /**
   * SportCountOutputType without action
   */
  export type SportCountOutputTypeCountGamesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: GameWhereInput
  }


  /**
   * Count Type TeamCountOutputType
   */

  export type TeamCountOutputType = {
    homeGames: number
    awayGames: number
    injuries: number
    profiles: number
  }

  export type TeamCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    homeGames?: boolean | TeamCountOutputTypeCountHomeGamesArgs
    awayGames?: boolean | TeamCountOutputTypeCountAwayGamesArgs
    injuries?: boolean | TeamCountOutputTypeCountInjuriesArgs
    profiles?: boolean | TeamCountOutputTypeCountProfilesArgs
  }

  // Custom InputTypes
  /**
   * TeamCountOutputType without action
   */
  export type TeamCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamCountOutputType
     */
    select?: TeamCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * TeamCountOutputType without action
   */
  export type TeamCountOutputTypeCountHomeGamesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: GameWhereInput
  }

  /**
   * TeamCountOutputType without action
   */
  export type TeamCountOutputTypeCountAwayGamesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: GameWhereInput
  }

  /**
   * TeamCountOutputType without action
   */
  export type TeamCountOutputTypeCountInjuriesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: InjuryWhereInput
  }

  /**
   * TeamCountOutputType without action
   */
  export type TeamCountOutputTypeCountProfilesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TeamProfileWeeklyWhereInput
  }


  /**
   * Count Type MarketSnapshotCountOutputType
   */

  export type MarketSnapshotCountOutputType = {
    bookLines: number
  }

  export type MarketSnapshotCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    bookLines?: boolean | MarketSnapshotCountOutputTypeCountBookLinesArgs
  }

  // Custom InputTypes
  /**
   * MarketSnapshotCountOutputType without action
   */
  export type MarketSnapshotCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshotCountOutputType
     */
    select?: MarketSnapshotCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * MarketSnapshotCountOutputType without action
   */
  export type MarketSnapshotCountOutputTypeCountBookLinesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: BookLineWhereInput
  }


  /**
   * Models
   */

  /**
   * Model User
   */

  export type AggregateUser = {
    _count: UserCountAggregateOutputType | null
    _min: UserMinAggregateOutputType | null
    _max: UserMaxAggregateOutputType | null
  }

  export type UserMinAggregateOutputType = {
    id: string | null
    email: string | null
    emailVerified: Date | null
    name: string | null
    password: string | null
    image: string | null
    role: $Enums.UserRole | null
    subscriptionStatus: $Enums.SubscriptionStatus | null
    subscriptionPlan: string | null
    subscriptionStart: Date | null
    subscriptionEnd: Date | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type UserMaxAggregateOutputType = {
    id: string | null
    email: string | null
    emailVerified: Date | null
    name: string | null
    password: string | null
    image: string | null
    role: $Enums.UserRole | null
    subscriptionStatus: $Enums.SubscriptionStatus | null
    subscriptionPlan: string | null
    subscriptionStart: Date | null
    subscriptionEnd: Date | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type UserCountAggregateOutputType = {
    id: number
    email: number
    emailVerified: number
    name: number
    password: number
    image: number
    role: number
    subscriptionStatus: number
    subscriptionPlan: number
    subscriptionStart: number
    subscriptionEnd: number
    createdAt: number
    updatedAt: number
    _all: number
  }


  export type UserMinAggregateInputType = {
    id?: true
    email?: true
    emailVerified?: true
    name?: true
    password?: true
    image?: true
    role?: true
    subscriptionStatus?: true
    subscriptionPlan?: true
    subscriptionStart?: true
    subscriptionEnd?: true
    createdAt?: true
    updatedAt?: true
  }

  export type UserMaxAggregateInputType = {
    id?: true
    email?: true
    emailVerified?: true
    name?: true
    password?: true
    image?: true
    role?: true
    subscriptionStatus?: true
    subscriptionPlan?: true
    subscriptionStart?: true
    subscriptionEnd?: true
    createdAt?: true
    updatedAt?: true
  }

  export type UserCountAggregateInputType = {
    id?: true
    email?: true
    emailVerified?: true
    name?: true
    password?: true
    image?: true
    role?: true
    subscriptionStatus?: true
    subscriptionPlan?: true
    subscriptionStart?: true
    subscriptionEnd?: true
    createdAt?: true
    updatedAt?: true
    _all?: true
  }

  export type UserAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which User to aggregate.
     */
    where?: UserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Users to fetch.
     */
    orderBy?: UserOrderByWithRelationInput | UserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: UserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Users from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Users.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Users
    **/
    _count?: true | UserCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: UserMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: UserMaxAggregateInputType
  }

  export type GetUserAggregateType<T extends UserAggregateArgs> = {
        [P in keyof T & keyof AggregateUser]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateUser[P]>
      : GetScalarType<T[P], AggregateUser[P]>
  }




  export type UserGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: UserWhereInput
    orderBy?: UserOrderByWithAggregationInput | UserOrderByWithAggregationInput[]
    by: UserScalarFieldEnum[] | UserScalarFieldEnum
    having?: UserScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: UserCountAggregateInputType | true
    _min?: UserMinAggregateInputType
    _max?: UserMaxAggregateInputType
  }

  export type UserGroupByOutputType = {
    id: string
    email: string
    emailVerified: Date | null
    name: string | null
    password: string | null
    image: string | null
    role: $Enums.UserRole
    subscriptionStatus: $Enums.SubscriptionStatus | null
    subscriptionPlan: string | null
    subscriptionStart: Date | null
    subscriptionEnd: Date | null
    createdAt: Date
    updatedAt: Date
    _count: UserCountAggregateOutputType | null
    _min: UserMinAggregateOutputType | null
    _max: UserMaxAggregateOutputType | null
  }

  type GetUserGroupByPayload<T extends UserGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<UserGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof UserGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], UserGroupByOutputType[P]>
            : GetScalarType<T[P], UserGroupByOutputType[P]>
        }
      >
    >


  export type UserSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    email?: boolean
    emailVerified?: boolean
    name?: boolean
    password?: boolean
    image?: boolean
    role?: boolean
    subscriptionStatus?: boolean
    subscriptionPlan?: boolean
    subscriptionStart?: boolean
    subscriptionEnd?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    accounts?: boolean | User$accountsArgs<ExtArgs>
    sessions?: boolean | User$sessionsArgs<ExtArgs>
    _count?: boolean | UserCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["user"]>

  export type UserSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    email?: boolean
    emailVerified?: boolean
    name?: boolean
    password?: boolean
    image?: boolean
    role?: boolean
    subscriptionStatus?: boolean
    subscriptionPlan?: boolean
    subscriptionStart?: boolean
    subscriptionEnd?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["user"]>

  export type UserSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    email?: boolean
    emailVerified?: boolean
    name?: boolean
    password?: boolean
    image?: boolean
    role?: boolean
    subscriptionStatus?: boolean
    subscriptionPlan?: boolean
    subscriptionStart?: boolean
    subscriptionEnd?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["user"]>

  export type UserSelectScalar = {
    id?: boolean
    email?: boolean
    emailVerified?: boolean
    name?: boolean
    password?: boolean
    image?: boolean
    role?: boolean
    subscriptionStatus?: boolean
    subscriptionPlan?: boolean
    subscriptionStart?: boolean
    subscriptionEnd?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }

  export type UserOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "email" | "emailVerified" | "name" | "password" | "image" | "role" | "subscriptionStatus" | "subscriptionPlan" | "subscriptionStart" | "subscriptionEnd" | "createdAt" | "updatedAt", ExtArgs["result"]["user"]>
  export type UserInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    accounts?: boolean | User$accountsArgs<ExtArgs>
    sessions?: boolean | User$sessionsArgs<ExtArgs>
    _count?: boolean | UserCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type UserIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}
  export type UserIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}

  export type $UserPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "User"
    objects: {
      accounts: Prisma.$AccountPayload<ExtArgs>[]
      sessions: Prisma.$SessionPayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      email: string
      emailVerified: Date | null
      name: string | null
      password: string | null
      image: string | null
      role: $Enums.UserRole
      subscriptionStatus: $Enums.SubscriptionStatus | null
      subscriptionPlan: string | null
      subscriptionStart: Date | null
      subscriptionEnd: Date | null
      createdAt: Date
      updatedAt: Date
    }, ExtArgs["result"]["user"]>
    composites: {}
  }

  type UserGetPayload<S extends boolean | null | undefined | UserDefaultArgs> = $Result.GetResult<Prisma.$UserPayload, S>

  type UserCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<UserFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: UserCountAggregateInputType | true
    }

  export interface UserDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['User'], meta: { name: 'User' } }
    /**
     * Find zero or one User that matches the filter.
     * @param {UserFindUniqueArgs} args - Arguments to find a User
     * @example
     * // Get one User
     * const user = await prisma.user.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends UserFindUniqueArgs>(args: SelectSubset<T, UserFindUniqueArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one User that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {UserFindUniqueOrThrowArgs} args - Arguments to find a User
     * @example
     * // Get one User
     * const user = await prisma.user.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends UserFindUniqueOrThrowArgs>(args: SelectSubset<T, UserFindUniqueOrThrowArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first User that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserFindFirstArgs} args - Arguments to find a User
     * @example
     * // Get one User
     * const user = await prisma.user.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends UserFindFirstArgs>(args?: SelectSubset<T, UserFindFirstArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first User that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserFindFirstOrThrowArgs} args - Arguments to find a User
     * @example
     * // Get one User
     * const user = await prisma.user.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends UserFindFirstOrThrowArgs>(args?: SelectSubset<T, UserFindFirstOrThrowArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Users that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Users
     * const users = await prisma.user.findMany()
     * 
     * // Get first 10 Users
     * const users = await prisma.user.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const userWithIdOnly = await prisma.user.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends UserFindManyArgs>(args?: SelectSubset<T, UserFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a User.
     * @param {UserCreateArgs} args - Arguments to create a User.
     * @example
     * // Create one User
     * const User = await prisma.user.create({
     *   data: {
     *     // ... data to create a User
     *   }
     * })
     * 
     */
    create<T extends UserCreateArgs>(args: SelectSubset<T, UserCreateArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Users.
     * @param {UserCreateManyArgs} args - Arguments to create many Users.
     * @example
     * // Create many Users
     * const user = await prisma.user.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends UserCreateManyArgs>(args?: SelectSubset<T, UserCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Users and returns the data saved in the database.
     * @param {UserCreateManyAndReturnArgs} args - Arguments to create many Users.
     * @example
     * // Create many Users
     * const user = await prisma.user.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Users and only return the `id`
     * const userWithIdOnly = await prisma.user.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends UserCreateManyAndReturnArgs>(args?: SelectSubset<T, UserCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a User.
     * @param {UserDeleteArgs} args - Arguments to delete one User.
     * @example
     * // Delete one User
     * const User = await prisma.user.delete({
     *   where: {
     *     // ... filter to delete one User
     *   }
     * })
     * 
     */
    delete<T extends UserDeleteArgs>(args: SelectSubset<T, UserDeleteArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one User.
     * @param {UserUpdateArgs} args - Arguments to update one User.
     * @example
     * // Update one User
     * const user = await prisma.user.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends UserUpdateArgs>(args: SelectSubset<T, UserUpdateArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Users.
     * @param {UserDeleteManyArgs} args - Arguments to filter Users to delete.
     * @example
     * // Delete a few Users
     * const { count } = await prisma.user.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends UserDeleteManyArgs>(args?: SelectSubset<T, UserDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Users.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Users
     * const user = await prisma.user.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends UserUpdateManyArgs>(args: SelectSubset<T, UserUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Users and returns the data updated in the database.
     * @param {UserUpdateManyAndReturnArgs} args - Arguments to update many Users.
     * @example
     * // Update many Users
     * const user = await prisma.user.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Users and only return the `id`
     * const userWithIdOnly = await prisma.user.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends UserUpdateManyAndReturnArgs>(args: SelectSubset<T, UserUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one User.
     * @param {UserUpsertArgs} args - Arguments to update or create a User.
     * @example
     * // Update or create a User
     * const user = await prisma.user.upsert({
     *   create: {
     *     // ... data to create a User
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the User we want to update
     *   }
     * })
     */
    upsert<T extends UserUpsertArgs>(args: SelectSubset<T, UserUpsertArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Users.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserCountArgs} args - Arguments to filter Users to count.
     * @example
     * // Count the number of Users
     * const count = await prisma.user.count({
     *   where: {
     *     // ... the filter for the Users we want to count
     *   }
     * })
    **/
    count<T extends UserCountArgs>(
      args?: Subset<T, UserCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], UserCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a User.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends UserAggregateArgs>(args: Subset<T, UserAggregateArgs>): Prisma.PrismaPromise<GetUserAggregateType<T>>

    /**
     * Group by User.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {UserGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends UserGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: UserGroupByArgs['orderBy'] }
        : { orderBy?: UserGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, UserGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetUserGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the User model
   */
  readonly fields: UserFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for User.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__UserClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    accounts<T extends User$accountsArgs<ExtArgs> = {}>(args?: Subset<T, User$accountsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    sessions<T extends User$sessionsArgs<ExtArgs> = {}>(args?: Subset<T, User$sessionsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the User model
   */
  interface UserFieldRefs {
    readonly id: FieldRef<"User", 'String'>
    readonly email: FieldRef<"User", 'String'>
    readonly emailVerified: FieldRef<"User", 'DateTime'>
    readonly name: FieldRef<"User", 'String'>
    readonly password: FieldRef<"User", 'String'>
    readonly image: FieldRef<"User", 'String'>
    readonly role: FieldRef<"User", 'UserRole'>
    readonly subscriptionStatus: FieldRef<"User", 'SubscriptionStatus'>
    readonly subscriptionPlan: FieldRef<"User", 'String'>
    readonly subscriptionStart: FieldRef<"User", 'DateTime'>
    readonly subscriptionEnd: FieldRef<"User", 'DateTime'>
    readonly createdAt: FieldRef<"User", 'DateTime'>
    readonly updatedAt: FieldRef<"User", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * User findUnique
   */
  export type UserFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which User to fetch.
     */
    where: UserWhereUniqueInput
  }

  /**
   * User findUniqueOrThrow
   */
  export type UserFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which User to fetch.
     */
    where: UserWhereUniqueInput
  }

  /**
   * User findFirst
   */
  export type UserFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which User to fetch.
     */
    where?: UserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Users to fetch.
     */
    orderBy?: UserOrderByWithRelationInput | UserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Users.
     */
    cursor?: UserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Users from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Users.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Users.
     */
    distinct?: UserScalarFieldEnum | UserScalarFieldEnum[]
  }

  /**
   * User findFirstOrThrow
   */
  export type UserFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which User to fetch.
     */
    where?: UserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Users to fetch.
     */
    orderBy?: UserOrderByWithRelationInput | UserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Users.
     */
    cursor?: UserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Users from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Users.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Users.
     */
    distinct?: UserScalarFieldEnum | UserScalarFieldEnum[]
  }

  /**
   * User findMany
   */
  export type UserFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter, which Users to fetch.
     */
    where?: UserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Users to fetch.
     */
    orderBy?: UserOrderByWithRelationInput | UserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Users.
     */
    cursor?: UserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Users from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Users.
     */
    skip?: number
    distinct?: UserScalarFieldEnum | UserScalarFieldEnum[]
  }

  /**
   * User create
   */
  export type UserCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * The data needed to create a User.
     */
    data: XOR<UserCreateInput, UserUncheckedCreateInput>
  }

  /**
   * User createMany
   */
  export type UserCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Users.
     */
    data: UserCreateManyInput | UserCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * User createManyAndReturn
   */
  export type UserCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * The data used to create many Users.
     */
    data: UserCreateManyInput | UserCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * User update
   */
  export type UserUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * The data needed to update a User.
     */
    data: XOR<UserUpdateInput, UserUncheckedUpdateInput>
    /**
     * Choose, which User to update.
     */
    where: UserWhereUniqueInput
  }

  /**
   * User updateMany
   */
  export type UserUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Users.
     */
    data: XOR<UserUpdateManyMutationInput, UserUncheckedUpdateManyInput>
    /**
     * Filter which Users to update
     */
    where?: UserWhereInput
    /**
     * Limit how many Users to update.
     */
    limit?: number
  }

  /**
   * User updateManyAndReturn
   */
  export type UserUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * The data used to update Users.
     */
    data: XOR<UserUpdateManyMutationInput, UserUncheckedUpdateManyInput>
    /**
     * Filter which Users to update
     */
    where?: UserWhereInput
    /**
     * Limit how many Users to update.
     */
    limit?: number
  }

  /**
   * User upsert
   */
  export type UserUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * The filter to search for the User to update in case it exists.
     */
    where: UserWhereUniqueInput
    /**
     * In case the User found by the `where` argument doesn't exist, create a new User with this data.
     */
    create: XOR<UserCreateInput, UserUncheckedCreateInput>
    /**
     * In case the User was found with the provided `where` argument, update it with this data.
     */
    update: XOR<UserUpdateInput, UserUncheckedUpdateInput>
  }

  /**
   * User delete
   */
  export type UserDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
    /**
     * Filter which User to delete.
     */
    where: UserWhereUniqueInput
  }

  /**
   * User deleteMany
   */
  export type UserDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Users to delete
     */
    where?: UserWhereInput
    /**
     * Limit how many Users to delete.
     */
    limit?: number
  }

  /**
   * User.accounts
   */
  export type User$accountsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    where?: AccountWhereInput
    orderBy?: AccountOrderByWithRelationInput | AccountOrderByWithRelationInput[]
    cursor?: AccountWhereUniqueInput
    take?: number
    skip?: number
    distinct?: AccountScalarFieldEnum | AccountScalarFieldEnum[]
  }

  /**
   * User.sessions
   */
  export type User$sessionsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    where?: SessionWhereInput
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    cursor?: SessionWhereUniqueInput
    take?: number
    skip?: number
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * User without action
   */
  export type UserDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the User
     */
    select?: UserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the User
     */
    omit?: UserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: UserInclude<ExtArgs> | null
  }


  /**
   * Model Account
   */

  export type AggregateAccount = {
    _count: AccountCountAggregateOutputType | null
    _avg: AccountAvgAggregateOutputType | null
    _sum: AccountSumAggregateOutputType | null
    _min: AccountMinAggregateOutputType | null
    _max: AccountMaxAggregateOutputType | null
  }

  export type AccountAvgAggregateOutputType = {
    expires_at: number | null
  }

  export type AccountSumAggregateOutputType = {
    expires_at: number | null
  }

  export type AccountMinAggregateOutputType = {
    id: string | null
    userId: string | null
    type: string | null
    provider: string | null
    providerAccountId: string | null
    refresh_token: string | null
    access_token: string | null
    expires_at: number | null
    token_type: string | null
    scope: string | null
    id_token: string | null
    session_state: string | null
  }

  export type AccountMaxAggregateOutputType = {
    id: string | null
    userId: string | null
    type: string | null
    provider: string | null
    providerAccountId: string | null
    refresh_token: string | null
    access_token: string | null
    expires_at: number | null
    token_type: string | null
    scope: string | null
    id_token: string | null
    session_state: string | null
  }

  export type AccountCountAggregateOutputType = {
    id: number
    userId: number
    type: number
    provider: number
    providerAccountId: number
    refresh_token: number
    access_token: number
    expires_at: number
    token_type: number
    scope: number
    id_token: number
    session_state: number
    _all: number
  }


  export type AccountAvgAggregateInputType = {
    expires_at?: true
  }

  export type AccountSumAggregateInputType = {
    expires_at?: true
  }

  export type AccountMinAggregateInputType = {
    id?: true
    userId?: true
    type?: true
    provider?: true
    providerAccountId?: true
    refresh_token?: true
    access_token?: true
    expires_at?: true
    token_type?: true
    scope?: true
    id_token?: true
    session_state?: true
  }

  export type AccountMaxAggregateInputType = {
    id?: true
    userId?: true
    type?: true
    provider?: true
    providerAccountId?: true
    refresh_token?: true
    access_token?: true
    expires_at?: true
    token_type?: true
    scope?: true
    id_token?: true
    session_state?: true
  }

  export type AccountCountAggregateInputType = {
    id?: true
    userId?: true
    type?: true
    provider?: true
    providerAccountId?: true
    refresh_token?: true
    access_token?: true
    expires_at?: true
    token_type?: true
    scope?: true
    id_token?: true
    session_state?: true
    _all?: true
  }

  export type AccountAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Account to aggregate.
     */
    where?: AccountWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Accounts to fetch.
     */
    orderBy?: AccountOrderByWithRelationInput | AccountOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: AccountWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Accounts from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Accounts.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Accounts
    **/
    _count?: true | AccountCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to average
    **/
    _avg?: AccountAvgAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to sum
    **/
    _sum?: AccountSumAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: AccountMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: AccountMaxAggregateInputType
  }

  export type GetAccountAggregateType<T extends AccountAggregateArgs> = {
        [P in keyof T & keyof AggregateAccount]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateAccount[P]>
      : GetScalarType<T[P], AggregateAccount[P]>
  }




  export type AccountGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: AccountWhereInput
    orderBy?: AccountOrderByWithAggregationInput | AccountOrderByWithAggregationInput[]
    by: AccountScalarFieldEnum[] | AccountScalarFieldEnum
    having?: AccountScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: AccountCountAggregateInputType | true
    _avg?: AccountAvgAggregateInputType
    _sum?: AccountSumAggregateInputType
    _min?: AccountMinAggregateInputType
    _max?: AccountMaxAggregateInputType
  }

  export type AccountGroupByOutputType = {
    id: string
    userId: string
    type: string
    provider: string
    providerAccountId: string
    refresh_token: string | null
    access_token: string | null
    expires_at: number | null
    token_type: string | null
    scope: string | null
    id_token: string | null
    session_state: string | null
    _count: AccountCountAggregateOutputType | null
    _avg: AccountAvgAggregateOutputType | null
    _sum: AccountSumAggregateOutputType | null
    _min: AccountMinAggregateOutputType | null
    _max: AccountMaxAggregateOutputType | null
  }

  type GetAccountGroupByPayload<T extends AccountGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<AccountGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof AccountGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], AccountGroupByOutputType[P]>
            : GetScalarType<T[P], AccountGroupByOutputType[P]>
        }
      >
    >


  export type AccountSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    type?: boolean
    provider?: boolean
    providerAccountId?: boolean
    refresh_token?: boolean
    access_token?: boolean
    expires_at?: boolean
    token_type?: boolean
    scope?: boolean
    id_token?: boolean
    session_state?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["account"]>

  export type AccountSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    type?: boolean
    provider?: boolean
    providerAccountId?: boolean
    refresh_token?: boolean
    access_token?: boolean
    expires_at?: boolean
    token_type?: boolean
    scope?: boolean
    id_token?: boolean
    session_state?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["account"]>

  export type AccountSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    userId?: boolean
    type?: boolean
    provider?: boolean
    providerAccountId?: boolean
    refresh_token?: boolean
    access_token?: boolean
    expires_at?: boolean
    token_type?: boolean
    scope?: boolean
    id_token?: boolean
    session_state?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["account"]>

  export type AccountSelectScalar = {
    id?: boolean
    userId?: boolean
    type?: boolean
    provider?: boolean
    providerAccountId?: boolean
    refresh_token?: boolean
    access_token?: boolean
    expires_at?: boolean
    token_type?: boolean
    scope?: boolean
    id_token?: boolean
    session_state?: boolean
  }

  export type AccountOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "userId" | "type" | "provider" | "providerAccountId" | "refresh_token" | "access_token" | "expires_at" | "token_type" | "scope" | "id_token" | "session_state", ExtArgs["result"]["account"]>
  export type AccountInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type AccountIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type AccountIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }

  export type $AccountPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Account"
    objects: {
      user: Prisma.$UserPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      userId: string
      type: string
      provider: string
      providerAccountId: string
      refresh_token: string | null
      access_token: string | null
      expires_at: number | null
      token_type: string | null
      scope: string | null
      id_token: string | null
      session_state: string | null
    }, ExtArgs["result"]["account"]>
    composites: {}
  }

  type AccountGetPayload<S extends boolean | null | undefined | AccountDefaultArgs> = $Result.GetResult<Prisma.$AccountPayload, S>

  type AccountCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<AccountFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: AccountCountAggregateInputType | true
    }

  export interface AccountDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Account'], meta: { name: 'Account' } }
    /**
     * Find zero or one Account that matches the filter.
     * @param {AccountFindUniqueArgs} args - Arguments to find a Account
     * @example
     * // Get one Account
     * const account = await prisma.account.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends AccountFindUniqueArgs>(args: SelectSubset<T, AccountFindUniqueArgs<ExtArgs>>): Prisma__AccountClient<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Account that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {AccountFindUniqueOrThrowArgs} args - Arguments to find a Account
     * @example
     * // Get one Account
     * const account = await prisma.account.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends AccountFindUniqueOrThrowArgs>(args: SelectSubset<T, AccountFindUniqueOrThrowArgs<ExtArgs>>): Prisma__AccountClient<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Account that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AccountFindFirstArgs} args - Arguments to find a Account
     * @example
     * // Get one Account
     * const account = await prisma.account.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends AccountFindFirstArgs>(args?: SelectSubset<T, AccountFindFirstArgs<ExtArgs>>): Prisma__AccountClient<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Account that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AccountFindFirstOrThrowArgs} args - Arguments to find a Account
     * @example
     * // Get one Account
     * const account = await prisma.account.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends AccountFindFirstOrThrowArgs>(args?: SelectSubset<T, AccountFindFirstOrThrowArgs<ExtArgs>>): Prisma__AccountClient<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Accounts that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AccountFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Accounts
     * const accounts = await prisma.account.findMany()
     * 
     * // Get first 10 Accounts
     * const accounts = await prisma.account.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const accountWithIdOnly = await prisma.account.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends AccountFindManyArgs>(args?: SelectSubset<T, AccountFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Account.
     * @param {AccountCreateArgs} args - Arguments to create a Account.
     * @example
     * // Create one Account
     * const Account = await prisma.account.create({
     *   data: {
     *     // ... data to create a Account
     *   }
     * })
     * 
     */
    create<T extends AccountCreateArgs>(args: SelectSubset<T, AccountCreateArgs<ExtArgs>>): Prisma__AccountClient<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Accounts.
     * @param {AccountCreateManyArgs} args - Arguments to create many Accounts.
     * @example
     * // Create many Accounts
     * const account = await prisma.account.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends AccountCreateManyArgs>(args?: SelectSubset<T, AccountCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Accounts and returns the data saved in the database.
     * @param {AccountCreateManyAndReturnArgs} args - Arguments to create many Accounts.
     * @example
     * // Create many Accounts
     * const account = await prisma.account.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Accounts and only return the `id`
     * const accountWithIdOnly = await prisma.account.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends AccountCreateManyAndReturnArgs>(args?: SelectSubset<T, AccountCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Account.
     * @param {AccountDeleteArgs} args - Arguments to delete one Account.
     * @example
     * // Delete one Account
     * const Account = await prisma.account.delete({
     *   where: {
     *     // ... filter to delete one Account
     *   }
     * })
     * 
     */
    delete<T extends AccountDeleteArgs>(args: SelectSubset<T, AccountDeleteArgs<ExtArgs>>): Prisma__AccountClient<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Account.
     * @param {AccountUpdateArgs} args - Arguments to update one Account.
     * @example
     * // Update one Account
     * const account = await prisma.account.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends AccountUpdateArgs>(args: SelectSubset<T, AccountUpdateArgs<ExtArgs>>): Prisma__AccountClient<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Accounts.
     * @param {AccountDeleteManyArgs} args - Arguments to filter Accounts to delete.
     * @example
     * // Delete a few Accounts
     * const { count } = await prisma.account.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends AccountDeleteManyArgs>(args?: SelectSubset<T, AccountDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Accounts.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AccountUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Accounts
     * const account = await prisma.account.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends AccountUpdateManyArgs>(args: SelectSubset<T, AccountUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Accounts and returns the data updated in the database.
     * @param {AccountUpdateManyAndReturnArgs} args - Arguments to update many Accounts.
     * @example
     * // Update many Accounts
     * const account = await prisma.account.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Accounts and only return the `id`
     * const accountWithIdOnly = await prisma.account.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends AccountUpdateManyAndReturnArgs>(args: SelectSubset<T, AccountUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Account.
     * @param {AccountUpsertArgs} args - Arguments to update or create a Account.
     * @example
     * // Update or create a Account
     * const account = await prisma.account.upsert({
     *   create: {
     *     // ... data to create a Account
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Account we want to update
     *   }
     * })
     */
    upsert<T extends AccountUpsertArgs>(args: SelectSubset<T, AccountUpsertArgs<ExtArgs>>): Prisma__AccountClient<$Result.GetResult<Prisma.$AccountPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Accounts.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AccountCountArgs} args - Arguments to filter Accounts to count.
     * @example
     * // Count the number of Accounts
     * const count = await prisma.account.count({
     *   where: {
     *     // ... the filter for the Accounts we want to count
     *   }
     * })
    **/
    count<T extends AccountCountArgs>(
      args?: Subset<T, AccountCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], AccountCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Account.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AccountAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends AccountAggregateArgs>(args: Subset<T, AccountAggregateArgs>): Prisma.PrismaPromise<GetAccountAggregateType<T>>

    /**
     * Group by Account.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AccountGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends AccountGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: AccountGroupByArgs['orderBy'] }
        : { orderBy?: AccountGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, AccountGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetAccountGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Account model
   */
  readonly fields: AccountFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Account.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__AccountClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    user<T extends UserDefaultArgs<ExtArgs> = {}>(args?: Subset<T, UserDefaultArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Account model
   */
  interface AccountFieldRefs {
    readonly id: FieldRef<"Account", 'String'>
    readonly userId: FieldRef<"Account", 'String'>
    readonly type: FieldRef<"Account", 'String'>
    readonly provider: FieldRef<"Account", 'String'>
    readonly providerAccountId: FieldRef<"Account", 'String'>
    readonly refresh_token: FieldRef<"Account", 'String'>
    readonly access_token: FieldRef<"Account", 'String'>
    readonly expires_at: FieldRef<"Account", 'Int'>
    readonly token_type: FieldRef<"Account", 'String'>
    readonly scope: FieldRef<"Account", 'String'>
    readonly id_token: FieldRef<"Account", 'String'>
    readonly session_state: FieldRef<"Account", 'String'>
  }
    

  // Custom InputTypes
  /**
   * Account findUnique
   */
  export type AccountFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    /**
     * Filter, which Account to fetch.
     */
    where: AccountWhereUniqueInput
  }

  /**
   * Account findUniqueOrThrow
   */
  export type AccountFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    /**
     * Filter, which Account to fetch.
     */
    where: AccountWhereUniqueInput
  }

  /**
   * Account findFirst
   */
  export type AccountFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    /**
     * Filter, which Account to fetch.
     */
    where?: AccountWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Accounts to fetch.
     */
    orderBy?: AccountOrderByWithRelationInput | AccountOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Accounts.
     */
    cursor?: AccountWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Accounts from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Accounts.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Accounts.
     */
    distinct?: AccountScalarFieldEnum | AccountScalarFieldEnum[]
  }

  /**
   * Account findFirstOrThrow
   */
  export type AccountFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    /**
     * Filter, which Account to fetch.
     */
    where?: AccountWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Accounts to fetch.
     */
    orderBy?: AccountOrderByWithRelationInput | AccountOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Accounts.
     */
    cursor?: AccountWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Accounts from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Accounts.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Accounts.
     */
    distinct?: AccountScalarFieldEnum | AccountScalarFieldEnum[]
  }

  /**
   * Account findMany
   */
  export type AccountFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    /**
     * Filter, which Accounts to fetch.
     */
    where?: AccountWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Accounts to fetch.
     */
    orderBy?: AccountOrderByWithRelationInput | AccountOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Accounts.
     */
    cursor?: AccountWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Accounts from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Accounts.
     */
    skip?: number
    distinct?: AccountScalarFieldEnum | AccountScalarFieldEnum[]
  }

  /**
   * Account create
   */
  export type AccountCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    /**
     * The data needed to create a Account.
     */
    data: XOR<AccountCreateInput, AccountUncheckedCreateInput>
  }

  /**
   * Account createMany
   */
  export type AccountCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Accounts.
     */
    data: AccountCreateManyInput | AccountCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Account createManyAndReturn
   */
  export type AccountCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * The data used to create many Accounts.
     */
    data: AccountCreateManyInput | AccountCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Account update
   */
  export type AccountUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    /**
     * The data needed to update a Account.
     */
    data: XOR<AccountUpdateInput, AccountUncheckedUpdateInput>
    /**
     * Choose, which Account to update.
     */
    where: AccountWhereUniqueInput
  }

  /**
   * Account updateMany
   */
  export type AccountUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Accounts.
     */
    data: XOR<AccountUpdateManyMutationInput, AccountUncheckedUpdateManyInput>
    /**
     * Filter which Accounts to update
     */
    where?: AccountWhereInput
    /**
     * Limit how many Accounts to update.
     */
    limit?: number
  }

  /**
   * Account updateManyAndReturn
   */
  export type AccountUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * The data used to update Accounts.
     */
    data: XOR<AccountUpdateManyMutationInput, AccountUncheckedUpdateManyInput>
    /**
     * Filter which Accounts to update
     */
    where?: AccountWhereInput
    /**
     * Limit how many Accounts to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Account upsert
   */
  export type AccountUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    /**
     * The filter to search for the Account to update in case it exists.
     */
    where: AccountWhereUniqueInput
    /**
     * In case the Account found by the `where` argument doesn't exist, create a new Account with this data.
     */
    create: XOR<AccountCreateInput, AccountUncheckedCreateInput>
    /**
     * In case the Account was found with the provided `where` argument, update it with this data.
     */
    update: XOR<AccountUpdateInput, AccountUncheckedUpdateInput>
  }

  /**
   * Account delete
   */
  export type AccountDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
    /**
     * Filter which Account to delete.
     */
    where: AccountWhereUniqueInput
  }

  /**
   * Account deleteMany
   */
  export type AccountDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Accounts to delete
     */
    where?: AccountWhereInput
    /**
     * Limit how many Accounts to delete.
     */
    limit?: number
  }

  /**
   * Account without action
   */
  export type AccountDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Account
     */
    select?: AccountSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Account
     */
    omit?: AccountOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AccountInclude<ExtArgs> | null
  }


  /**
   * Model Session
   */

  export type AggregateSession = {
    _count: SessionCountAggregateOutputType | null
    _min: SessionMinAggregateOutputType | null
    _max: SessionMaxAggregateOutputType | null
  }

  export type SessionMinAggregateOutputType = {
    id: string | null
    sessionToken: string | null
    userId: string | null
    expires: Date | null
  }

  export type SessionMaxAggregateOutputType = {
    id: string | null
    sessionToken: string | null
    userId: string | null
    expires: Date | null
  }

  export type SessionCountAggregateOutputType = {
    id: number
    sessionToken: number
    userId: number
    expires: number
    _all: number
  }


  export type SessionMinAggregateInputType = {
    id?: true
    sessionToken?: true
    userId?: true
    expires?: true
  }

  export type SessionMaxAggregateInputType = {
    id?: true
    sessionToken?: true
    userId?: true
    expires?: true
  }

  export type SessionCountAggregateInputType = {
    id?: true
    sessionToken?: true
    userId?: true
    expires?: true
    _all?: true
  }

  export type SessionAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Session to aggregate.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Sessions
    **/
    _count?: true | SessionCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: SessionMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: SessionMaxAggregateInputType
  }

  export type GetSessionAggregateType<T extends SessionAggregateArgs> = {
        [P in keyof T & keyof AggregateSession]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateSession[P]>
      : GetScalarType<T[P], AggregateSession[P]>
  }




  export type SessionGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: SessionWhereInput
    orderBy?: SessionOrderByWithAggregationInput | SessionOrderByWithAggregationInput[]
    by: SessionScalarFieldEnum[] | SessionScalarFieldEnum
    having?: SessionScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: SessionCountAggregateInputType | true
    _min?: SessionMinAggregateInputType
    _max?: SessionMaxAggregateInputType
  }

  export type SessionGroupByOutputType = {
    id: string
    sessionToken: string
    userId: string
    expires: Date
    _count: SessionCountAggregateOutputType | null
    _min: SessionMinAggregateOutputType | null
    _max: SessionMaxAggregateOutputType | null
  }

  type GetSessionGroupByPayload<T extends SessionGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<SessionGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof SessionGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], SessionGroupByOutputType[P]>
            : GetScalarType<T[P], SessionGroupByOutputType[P]>
        }
      >
    >


  export type SessionSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    sessionToken?: boolean
    userId?: boolean
    expires?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["session"]>

  export type SessionSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    sessionToken?: boolean
    userId?: boolean
    expires?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["session"]>

  export type SessionSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    sessionToken?: boolean
    userId?: boolean
    expires?: boolean
    user?: boolean | UserDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["session"]>

  export type SessionSelectScalar = {
    id?: boolean
    sessionToken?: boolean
    userId?: boolean
    expires?: boolean
  }

  export type SessionOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "sessionToken" | "userId" | "expires", ExtArgs["result"]["session"]>
  export type SessionInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type SessionIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }
  export type SessionIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    user?: boolean | UserDefaultArgs<ExtArgs>
  }

  export type $SessionPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Session"
    objects: {
      user: Prisma.$UserPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      sessionToken: string
      userId: string
      expires: Date
    }, ExtArgs["result"]["session"]>
    composites: {}
  }

  type SessionGetPayload<S extends boolean | null | undefined | SessionDefaultArgs> = $Result.GetResult<Prisma.$SessionPayload, S>

  type SessionCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<SessionFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: SessionCountAggregateInputType | true
    }

  export interface SessionDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Session'], meta: { name: 'Session' } }
    /**
     * Find zero or one Session that matches the filter.
     * @param {SessionFindUniqueArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends SessionFindUniqueArgs>(args: SelectSubset<T, SessionFindUniqueArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Session that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {SessionFindUniqueOrThrowArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends SessionFindUniqueOrThrowArgs>(args: SelectSubset<T, SessionFindUniqueOrThrowArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Session that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionFindFirstArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends SessionFindFirstArgs>(args?: SelectSubset<T, SessionFindFirstArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Session that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionFindFirstOrThrowArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends SessionFindFirstOrThrowArgs>(args?: SelectSubset<T, SessionFindFirstOrThrowArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Sessions that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Sessions
     * const sessions = await prisma.session.findMany()
     * 
     * // Get first 10 Sessions
     * const sessions = await prisma.session.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const sessionWithIdOnly = await prisma.session.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends SessionFindManyArgs>(args?: SelectSubset<T, SessionFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Session.
     * @param {SessionCreateArgs} args - Arguments to create a Session.
     * @example
     * // Create one Session
     * const Session = await prisma.session.create({
     *   data: {
     *     // ... data to create a Session
     *   }
     * })
     * 
     */
    create<T extends SessionCreateArgs>(args: SelectSubset<T, SessionCreateArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Sessions.
     * @param {SessionCreateManyArgs} args - Arguments to create many Sessions.
     * @example
     * // Create many Sessions
     * const session = await prisma.session.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends SessionCreateManyArgs>(args?: SelectSubset<T, SessionCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Sessions and returns the data saved in the database.
     * @param {SessionCreateManyAndReturnArgs} args - Arguments to create many Sessions.
     * @example
     * // Create many Sessions
     * const session = await prisma.session.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Sessions and only return the `id`
     * const sessionWithIdOnly = await prisma.session.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends SessionCreateManyAndReturnArgs>(args?: SelectSubset<T, SessionCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Session.
     * @param {SessionDeleteArgs} args - Arguments to delete one Session.
     * @example
     * // Delete one Session
     * const Session = await prisma.session.delete({
     *   where: {
     *     // ... filter to delete one Session
     *   }
     * })
     * 
     */
    delete<T extends SessionDeleteArgs>(args: SelectSubset<T, SessionDeleteArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Session.
     * @param {SessionUpdateArgs} args - Arguments to update one Session.
     * @example
     * // Update one Session
     * const session = await prisma.session.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends SessionUpdateArgs>(args: SelectSubset<T, SessionUpdateArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Sessions.
     * @param {SessionDeleteManyArgs} args - Arguments to filter Sessions to delete.
     * @example
     * // Delete a few Sessions
     * const { count } = await prisma.session.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends SessionDeleteManyArgs>(args?: SelectSubset<T, SessionDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Sessions.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Sessions
     * const session = await prisma.session.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends SessionUpdateManyArgs>(args: SelectSubset<T, SessionUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Sessions and returns the data updated in the database.
     * @param {SessionUpdateManyAndReturnArgs} args - Arguments to update many Sessions.
     * @example
     * // Update many Sessions
     * const session = await prisma.session.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Sessions and only return the `id`
     * const sessionWithIdOnly = await prisma.session.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends SessionUpdateManyAndReturnArgs>(args: SelectSubset<T, SessionUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Session.
     * @param {SessionUpsertArgs} args - Arguments to update or create a Session.
     * @example
     * // Update or create a Session
     * const session = await prisma.session.upsert({
     *   create: {
     *     // ... data to create a Session
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Session we want to update
     *   }
     * })
     */
    upsert<T extends SessionUpsertArgs>(args: SelectSubset<T, SessionUpsertArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Sessions.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionCountArgs} args - Arguments to filter Sessions to count.
     * @example
     * // Count the number of Sessions
     * const count = await prisma.session.count({
     *   where: {
     *     // ... the filter for the Sessions we want to count
     *   }
     * })
    **/
    count<T extends SessionCountArgs>(
      args?: Subset<T, SessionCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], SessionCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Session.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends SessionAggregateArgs>(args: Subset<T, SessionAggregateArgs>): Prisma.PrismaPromise<GetSessionAggregateType<T>>

    /**
     * Group by Session.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends SessionGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: SessionGroupByArgs['orderBy'] }
        : { orderBy?: SessionGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, SessionGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetSessionGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Session model
   */
  readonly fields: SessionFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Session.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__SessionClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    user<T extends UserDefaultArgs<ExtArgs> = {}>(args?: Subset<T, UserDefaultArgs<ExtArgs>>): Prisma__UserClient<$Result.GetResult<Prisma.$UserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Session model
   */
  interface SessionFieldRefs {
    readonly id: FieldRef<"Session", 'String'>
    readonly sessionToken: FieldRef<"Session", 'String'>
    readonly userId: FieldRef<"Session", 'String'>
    readonly expires: FieldRef<"Session", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * Session findUnique
   */
  export type SessionFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session findUniqueOrThrow
   */
  export type SessionFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session findFirst
   */
  export type SessionFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Sessions.
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Sessions.
     */
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Session findFirstOrThrow
   */
  export type SessionFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Sessions.
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Sessions.
     */
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Session findMany
   */
  export type SessionFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Sessions to fetch.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Sessions.
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Session create
   */
  export type SessionCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * The data needed to create a Session.
     */
    data: XOR<SessionCreateInput, SessionUncheckedCreateInput>
  }

  /**
   * Session createMany
   */
  export type SessionCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Sessions.
     */
    data: SessionCreateManyInput | SessionCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Session createManyAndReturn
   */
  export type SessionCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * The data used to create many Sessions.
     */
    data: SessionCreateManyInput | SessionCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Session update
   */
  export type SessionUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * The data needed to update a Session.
     */
    data: XOR<SessionUpdateInput, SessionUncheckedUpdateInput>
    /**
     * Choose, which Session to update.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session updateMany
   */
  export type SessionUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Sessions.
     */
    data: XOR<SessionUpdateManyMutationInput, SessionUncheckedUpdateManyInput>
    /**
     * Filter which Sessions to update
     */
    where?: SessionWhereInput
    /**
     * Limit how many Sessions to update.
     */
    limit?: number
  }

  /**
   * Session updateManyAndReturn
   */
  export type SessionUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * The data used to update Sessions.
     */
    data: XOR<SessionUpdateManyMutationInput, SessionUncheckedUpdateManyInput>
    /**
     * Filter which Sessions to update
     */
    where?: SessionWhereInput
    /**
     * Limit how many Sessions to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Session upsert
   */
  export type SessionUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * The filter to search for the Session to update in case it exists.
     */
    where: SessionWhereUniqueInput
    /**
     * In case the Session found by the `where` argument doesn't exist, create a new Session with this data.
     */
    create: XOR<SessionCreateInput, SessionUncheckedCreateInput>
    /**
     * In case the Session was found with the provided `where` argument, update it with this data.
     */
    update: XOR<SessionUpdateInput, SessionUncheckedUpdateInput>
  }

  /**
   * Session delete
   */
  export type SessionDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter which Session to delete.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session deleteMany
   */
  export type SessionDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Sessions to delete
     */
    where?: SessionWhereInput
    /**
     * Limit how many Sessions to delete.
     */
    limit?: number
  }

  /**
   * Session without action
   */
  export type SessionDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
  }


  /**
   * Model VerificationToken
   */

  export type AggregateVerificationToken = {
    _count: VerificationTokenCountAggregateOutputType | null
    _min: VerificationTokenMinAggregateOutputType | null
    _max: VerificationTokenMaxAggregateOutputType | null
  }

  export type VerificationTokenMinAggregateOutputType = {
    identifier: string | null
    token: string | null
    expires: Date | null
  }

  export type VerificationTokenMaxAggregateOutputType = {
    identifier: string | null
    token: string | null
    expires: Date | null
  }

  export type VerificationTokenCountAggregateOutputType = {
    identifier: number
    token: number
    expires: number
    _all: number
  }


  export type VerificationTokenMinAggregateInputType = {
    identifier?: true
    token?: true
    expires?: true
  }

  export type VerificationTokenMaxAggregateInputType = {
    identifier?: true
    token?: true
    expires?: true
  }

  export type VerificationTokenCountAggregateInputType = {
    identifier?: true
    token?: true
    expires?: true
    _all?: true
  }

  export type VerificationTokenAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which VerificationToken to aggregate.
     */
    where?: VerificationTokenWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of VerificationTokens to fetch.
     */
    orderBy?: VerificationTokenOrderByWithRelationInput | VerificationTokenOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: VerificationTokenWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` VerificationTokens from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` VerificationTokens.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned VerificationTokens
    **/
    _count?: true | VerificationTokenCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: VerificationTokenMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: VerificationTokenMaxAggregateInputType
  }

  export type GetVerificationTokenAggregateType<T extends VerificationTokenAggregateArgs> = {
        [P in keyof T & keyof AggregateVerificationToken]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateVerificationToken[P]>
      : GetScalarType<T[P], AggregateVerificationToken[P]>
  }




  export type VerificationTokenGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: VerificationTokenWhereInput
    orderBy?: VerificationTokenOrderByWithAggregationInput | VerificationTokenOrderByWithAggregationInput[]
    by: VerificationTokenScalarFieldEnum[] | VerificationTokenScalarFieldEnum
    having?: VerificationTokenScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: VerificationTokenCountAggregateInputType | true
    _min?: VerificationTokenMinAggregateInputType
    _max?: VerificationTokenMaxAggregateInputType
  }

  export type VerificationTokenGroupByOutputType = {
    identifier: string
    token: string
    expires: Date
    _count: VerificationTokenCountAggregateOutputType | null
    _min: VerificationTokenMinAggregateOutputType | null
    _max: VerificationTokenMaxAggregateOutputType | null
  }

  type GetVerificationTokenGroupByPayload<T extends VerificationTokenGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<VerificationTokenGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof VerificationTokenGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], VerificationTokenGroupByOutputType[P]>
            : GetScalarType<T[P], VerificationTokenGroupByOutputType[P]>
        }
      >
    >


  export type VerificationTokenSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    identifier?: boolean
    token?: boolean
    expires?: boolean
  }, ExtArgs["result"]["verificationToken"]>

  export type VerificationTokenSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    identifier?: boolean
    token?: boolean
    expires?: boolean
  }, ExtArgs["result"]["verificationToken"]>

  export type VerificationTokenSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    identifier?: boolean
    token?: boolean
    expires?: boolean
  }, ExtArgs["result"]["verificationToken"]>

  export type VerificationTokenSelectScalar = {
    identifier?: boolean
    token?: boolean
    expires?: boolean
  }

  export type VerificationTokenOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"identifier" | "token" | "expires", ExtArgs["result"]["verificationToken"]>

  export type $VerificationTokenPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "VerificationToken"
    objects: {}
    scalars: $Extensions.GetPayloadResult<{
      identifier: string
      token: string
      expires: Date
    }, ExtArgs["result"]["verificationToken"]>
    composites: {}
  }

  type VerificationTokenGetPayload<S extends boolean | null | undefined | VerificationTokenDefaultArgs> = $Result.GetResult<Prisma.$VerificationTokenPayload, S>

  type VerificationTokenCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<VerificationTokenFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: VerificationTokenCountAggregateInputType | true
    }

  export interface VerificationTokenDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['VerificationToken'], meta: { name: 'VerificationToken' } }
    /**
     * Find zero or one VerificationToken that matches the filter.
     * @param {VerificationTokenFindUniqueArgs} args - Arguments to find a VerificationToken
     * @example
     * // Get one VerificationToken
     * const verificationToken = await prisma.verificationToken.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends VerificationTokenFindUniqueArgs>(args: SelectSubset<T, VerificationTokenFindUniqueArgs<ExtArgs>>): Prisma__VerificationTokenClient<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one VerificationToken that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {VerificationTokenFindUniqueOrThrowArgs} args - Arguments to find a VerificationToken
     * @example
     * // Get one VerificationToken
     * const verificationToken = await prisma.verificationToken.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends VerificationTokenFindUniqueOrThrowArgs>(args: SelectSubset<T, VerificationTokenFindUniqueOrThrowArgs<ExtArgs>>): Prisma__VerificationTokenClient<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first VerificationToken that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {VerificationTokenFindFirstArgs} args - Arguments to find a VerificationToken
     * @example
     * // Get one VerificationToken
     * const verificationToken = await prisma.verificationToken.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends VerificationTokenFindFirstArgs>(args?: SelectSubset<T, VerificationTokenFindFirstArgs<ExtArgs>>): Prisma__VerificationTokenClient<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first VerificationToken that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {VerificationTokenFindFirstOrThrowArgs} args - Arguments to find a VerificationToken
     * @example
     * // Get one VerificationToken
     * const verificationToken = await prisma.verificationToken.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends VerificationTokenFindFirstOrThrowArgs>(args?: SelectSubset<T, VerificationTokenFindFirstOrThrowArgs<ExtArgs>>): Prisma__VerificationTokenClient<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more VerificationTokens that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {VerificationTokenFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all VerificationTokens
     * const verificationTokens = await prisma.verificationToken.findMany()
     * 
     * // Get first 10 VerificationTokens
     * const verificationTokens = await prisma.verificationToken.findMany({ take: 10 })
     * 
     * // Only select the `identifier`
     * const verificationTokenWithIdentifierOnly = await prisma.verificationToken.findMany({ select: { identifier: true } })
     * 
     */
    findMany<T extends VerificationTokenFindManyArgs>(args?: SelectSubset<T, VerificationTokenFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a VerificationToken.
     * @param {VerificationTokenCreateArgs} args - Arguments to create a VerificationToken.
     * @example
     * // Create one VerificationToken
     * const VerificationToken = await prisma.verificationToken.create({
     *   data: {
     *     // ... data to create a VerificationToken
     *   }
     * })
     * 
     */
    create<T extends VerificationTokenCreateArgs>(args: SelectSubset<T, VerificationTokenCreateArgs<ExtArgs>>): Prisma__VerificationTokenClient<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many VerificationTokens.
     * @param {VerificationTokenCreateManyArgs} args - Arguments to create many VerificationTokens.
     * @example
     * // Create many VerificationTokens
     * const verificationToken = await prisma.verificationToken.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends VerificationTokenCreateManyArgs>(args?: SelectSubset<T, VerificationTokenCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many VerificationTokens and returns the data saved in the database.
     * @param {VerificationTokenCreateManyAndReturnArgs} args - Arguments to create many VerificationTokens.
     * @example
     * // Create many VerificationTokens
     * const verificationToken = await prisma.verificationToken.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many VerificationTokens and only return the `identifier`
     * const verificationTokenWithIdentifierOnly = await prisma.verificationToken.createManyAndReturn({
     *   select: { identifier: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends VerificationTokenCreateManyAndReturnArgs>(args?: SelectSubset<T, VerificationTokenCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a VerificationToken.
     * @param {VerificationTokenDeleteArgs} args - Arguments to delete one VerificationToken.
     * @example
     * // Delete one VerificationToken
     * const VerificationToken = await prisma.verificationToken.delete({
     *   where: {
     *     // ... filter to delete one VerificationToken
     *   }
     * })
     * 
     */
    delete<T extends VerificationTokenDeleteArgs>(args: SelectSubset<T, VerificationTokenDeleteArgs<ExtArgs>>): Prisma__VerificationTokenClient<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one VerificationToken.
     * @param {VerificationTokenUpdateArgs} args - Arguments to update one VerificationToken.
     * @example
     * // Update one VerificationToken
     * const verificationToken = await prisma.verificationToken.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends VerificationTokenUpdateArgs>(args: SelectSubset<T, VerificationTokenUpdateArgs<ExtArgs>>): Prisma__VerificationTokenClient<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more VerificationTokens.
     * @param {VerificationTokenDeleteManyArgs} args - Arguments to filter VerificationTokens to delete.
     * @example
     * // Delete a few VerificationTokens
     * const { count } = await prisma.verificationToken.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends VerificationTokenDeleteManyArgs>(args?: SelectSubset<T, VerificationTokenDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more VerificationTokens.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {VerificationTokenUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many VerificationTokens
     * const verificationToken = await prisma.verificationToken.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends VerificationTokenUpdateManyArgs>(args: SelectSubset<T, VerificationTokenUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more VerificationTokens and returns the data updated in the database.
     * @param {VerificationTokenUpdateManyAndReturnArgs} args - Arguments to update many VerificationTokens.
     * @example
     * // Update many VerificationTokens
     * const verificationToken = await prisma.verificationToken.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more VerificationTokens and only return the `identifier`
     * const verificationTokenWithIdentifierOnly = await prisma.verificationToken.updateManyAndReturn({
     *   select: { identifier: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends VerificationTokenUpdateManyAndReturnArgs>(args: SelectSubset<T, VerificationTokenUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one VerificationToken.
     * @param {VerificationTokenUpsertArgs} args - Arguments to update or create a VerificationToken.
     * @example
     * // Update or create a VerificationToken
     * const verificationToken = await prisma.verificationToken.upsert({
     *   create: {
     *     // ... data to create a VerificationToken
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the VerificationToken we want to update
     *   }
     * })
     */
    upsert<T extends VerificationTokenUpsertArgs>(args: SelectSubset<T, VerificationTokenUpsertArgs<ExtArgs>>): Prisma__VerificationTokenClient<$Result.GetResult<Prisma.$VerificationTokenPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of VerificationTokens.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {VerificationTokenCountArgs} args - Arguments to filter VerificationTokens to count.
     * @example
     * // Count the number of VerificationTokens
     * const count = await prisma.verificationToken.count({
     *   where: {
     *     // ... the filter for the VerificationTokens we want to count
     *   }
     * })
    **/
    count<T extends VerificationTokenCountArgs>(
      args?: Subset<T, VerificationTokenCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], VerificationTokenCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a VerificationToken.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {VerificationTokenAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends VerificationTokenAggregateArgs>(args: Subset<T, VerificationTokenAggregateArgs>): Prisma.PrismaPromise<GetVerificationTokenAggregateType<T>>

    /**
     * Group by VerificationToken.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {VerificationTokenGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends VerificationTokenGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: VerificationTokenGroupByArgs['orderBy'] }
        : { orderBy?: VerificationTokenGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, VerificationTokenGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetVerificationTokenGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the VerificationToken model
   */
  readonly fields: VerificationTokenFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for VerificationToken.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__VerificationTokenClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the VerificationToken model
   */
  interface VerificationTokenFieldRefs {
    readonly identifier: FieldRef<"VerificationToken", 'String'>
    readonly token: FieldRef<"VerificationToken", 'String'>
    readonly expires: FieldRef<"VerificationToken", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * VerificationToken findUnique
   */
  export type VerificationTokenFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * Filter, which VerificationToken to fetch.
     */
    where: VerificationTokenWhereUniqueInput
  }

  /**
   * VerificationToken findUniqueOrThrow
   */
  export type VerificationTokenFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * Filter, which VerificationToken to fetch.
     */
    where: VerificationTokenWhereUniqueInput
  }

  /**
   * VerificationToken findFirst
   */
  export type VerificationTokenFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * Filter, which VerificationToken to fetch.
     */
    where?: VerificationTokenWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of VerificationTokens to fetch.
     */
    orderBy?: VerificationTokenOrderByWithRelationInput | VerificationTokenOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for VerificationTokens.
     */
    cursor?: VerificationTokenWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` VerificationTokens from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` VerificationTokens.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of VerificationTokens.
     */
    distinct?: VerificationTokenScalarFieldEnum | VerificationTokenScalarFieldEnum[]
  }

  /**
   * VerificationToken findFirstOrThrow
   */
  export type VerificationTokenFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * Filter, which VerificationToken to fetch.
     */
    where?: VerificationTokenWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of VerificationTokens to fetch.
     */
    orderBy?: VerificationTokenOrderByWithRelationInput | VerificationTokenOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for VerificationTokens.
     */
    cursor?: VerificationTokenWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` VerificationTokens from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` VerificationTokens.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of VerificationTokens.
     */
    distinct?: VerificationTokenScalarFieldEnum | VerificationTokenScalarFieldEnum[]
  }

  /**
   * VerificationToken findMany
   */
  export type VerificationTokenFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * Filter, which VerificationTokens to fetch.
     */
    where?: VerificationTokenWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of VerificationTokens to fetch.
     */
    orderBy?: VerificationTokenOrderByWithRelationInput | VerificationTokenOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing VerificationTokens.
     */
    cursor?: VerificationTokenWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` VerificationTokens from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` VerificationTokens.
     */
    skip?: number
    distinct?: VerificationTokenScalarFieldEnum | VerificationTokenScalarFieldEnum[]
  }

  /**
   * VerificationToken create
   */
  export type VerificationTokenCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * The data needed to create a VerificationToken.
     */
    data: XOR<VerificationTokenCreateInput, VerificationTokenUncheckedCreateInput>
  }

  /**
   * VerificationToken createMany
   */
  export type VerificationTokenCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many VerificationTokens.
     */
    data: VerificationTokenCreateManyInput | VerificationTokenCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * VerificationToken createManyAndReturn
   */
  export type VerificationTokenCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * The data used to create many VerificationTokens.
     */
    data: VerificationTokenCreateManyInput | VerificationTokenCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * VerificationToken update
   */
  export type VerificationTokenUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * The data needed to update a VerificationToken.
     */
    data: XOR<VerificationTokenUpdateInput, VerificationTokenUncheckedUpdateInput>
    /**
     * Choose, which VerificationToken to update.
     */
    where: VerificationTokenWhereUniqueInput
  }

  /**
   * VerificationToken updateMany
   */
  export type VerificationTokenUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update VerificationTokens.
     */
    data: XOR<VerificationTokenUpdateManyMutationInput, VerificationTokenUncheckedUpdateManyInput>
    /**
     * Filter which VerificationTokens to update
     */
    where?: VerificationTokenWhereInput
    /**
     * Limit how many VerificationTokens to update.
     */
    limit?: number
  }

  /**
   * VerificationToken updateManyAndReturn
   */
  export type VerificationTokenUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * The data used to update VerificationTokens.
     */
    data: XOR<VerificationTokenUpdateManyMutationInput, VerificationTokenUncheckedUpdateManyInput>
    /**
     * Filter which VerificationTokens to update
     */
    where?: VerificationTokenWhereInput
    /**
     * Limit how many VerificationTokens to update.
     */
    limit?: number
  }

  /**
   * VerificationToken upsert
   */
  export type VerificationTokenUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * The filter to search for the VerificationToken to update in case it exists.
     */
    where: VerificationTokenWhereUniqueInput
    /**
     * In case the VerificationToken found by the `where` argument doesn't exist, create a new VerificationToken with this data.
     */
    create: XOR<VerificationTokenCreateInput, VerificationTokenUncheckedCreateInput>
    /**
     * In case the VerificationToken was found with the provided `where` argument, update it with this data.
     */
    update: XOR<VerificationTokenUpdateInput, VerificationTokenUncheckedUpdateInput>
  }

  /**
   * VerificationToken delete
   */
  export type VerificationTokenDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
    /**
     * Filter which VerificationToken to delete.
     */
    where: VerificationTokenWhereUniqueInput
  }

  /**
   * VerificationToken deleteMany
   */
  export type VerificationTokenDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which VerificationTokens to delete
     */
    where?: VerificationTokenWhereInput
    /**
     * Limit how many VerificationTokens to delete.
     */
    limit?: number
  }

  /**
   * VerificationToken without action
   */
  export type VerificationTokenDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the VerificationToken
     */
    select?: VerificationTokenSelect<ExtArgs> | null
    /**
     * Omit specific fields from the VerificationToken
     */
    omit?: VerificationTokenOmit<ExtArgs> | null
  }


  /**
   * Model Sport
   */

  export type AggregateSport = {
    _count: SportCountAggregateOutputType | null
    _min: SportMinAggregateOutputType | null
    _max: SportMaxAggregateOutputType | null
  }

  export type SportMinAggregateOutputType = {
    id: string | null
    key: string | null
    name: string | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type SportMaxAggregateOutputType = {
    id: string | null
    key: string | null
    name: string | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type SportCountAggregateOutputType = {
    id: number
    key: number
    name: number
    createdAt: number
    updatedAt: number
    _all: number
  }


  export type SportMinAggregateInputType = {
    id?: true
    key?: true
    name?: true
    createdAt?: true
    updatedAt?: true
  }

  export type SportMaxAggregateInputType = {
    id?: true
    key?: true
    name?: true
    createdAt?: true
    updatedAt?: true
  }

  export type SportCountAggregateInputType = {
    id?: true
    key?: true
    name?: true
    createdAt?: true
    updatedAt?: true
    _all?: true
  }

  export type SportAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Sport to aggregate.
     */
    where?: SportWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sports to fetch.
     */
    orderBy?: SportOrderByWithRelationInput | SportOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: SportWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sports from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sports.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Sports
    **/
    _count?: true | SportCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: SportMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: SportMaxAggregateInputType
  }

  export type GetSportAggregateType<T extends SportAggregateArgs> = {
        [P in keyof T & keyof AggregateSport]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateSport[P]>
      : GetScalarType<T[P], AggregateSport[P]>
  }




  export type SportGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: SportWhereInput
    orderBy?: SportOrderByWithAggregationInput | SportOrderByWithAggregationInput[]
    by: SportScalarFieldEnum[] | SportScalarFieldEnum
    having?: SportScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: SportCountAggregateInputType | true
    _min?: SportMinAggregateInputType
    _max?: SportMaxAggregateInputType
  }

  export type SportGroupByOutputType = {
    id: string
    key: string
    name: string
    createdAt: Date
    updatedAt: Date
    _count: SportCountAggregateOutputType | null
    _min: SportMinAggregateOutputType | null
    _max: SportMaxAggregateOutputType | null
  }

  type GetSportGroupByPayload<T extends SportGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<SportGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof SportGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], SportGroupByOutputType[P]>
            : GetScalarType<T[P], SportGroupByOutputType[P]>
        }
      >
    >


  export type SportSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    key?: boolean
    name?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    teams?: boolean | Sport$teamsArgs<ExtArgs>
    games?: boolean | Sport$gamesArgs<ExtArgs>
    _count?: boolean | SportCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["sport"]>

  export type SportSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    key?: boolean
    name?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["sport"]>

  export type SportSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    key?: boolean
    name?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }, ExtArgs["result"]["sport"]>

  export type SportSelectScalar = {
    id?: boolean
    key?: boolean
    name?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }

  export type SportOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "key" | "name" | "createdAt" | "updatedAt", ExtArgs["result"]["sport"]>
  export type SportInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    teams?: boolean | Sport$teamsArgs<ExtArgs>
    games?: boolean | Sport$gamesArgs<ExtArgs>
    _count?: boolean | SportCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type SportIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}
  export type SportIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}

  export type $SportPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Sport"
    objects: {
      teams: Prisma.$TeamPayload<ExtArgs>[]
      games: Prisma.$GamePayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      key: string
      name: string
      createdAt: Date
      updatedAt: Date
    }, ExtArgs["result"]["sport"]>
    composites: {}
  }

  type SportGetPayload<S extends boolean | null | undefined | SportDefaultArgs> = $Result.GetResult<Prisma.$SportPayload, S>

  type SportCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<SportFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: SportCountAggregateInputType | true
    }

  export interface SportDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Sport'], meta: { name: 'Sport' } }
    /**
     * Find zero or one Sport that matches the filter.
     * @param {SportFindUniqueArgs} args - Arguments to find a Sport
     * @example
     * // Get one Sport
     * const sport = await prisma.sport.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends SportFindUniqueArgs>(args: SelectSubset<T, SportFindUniqueArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Sport that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {SportFindUniqueOrThrowArgs} args - Arguments to find a Sport
     * @example
     * // Get one Sport
     * const sport = await prisma.sport.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends SportFindUniqueOrThrowArgs>(args: SelectSubset<T, SportFindUniqueOrThrowArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Sport that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SportFindFirstArgs} args - Arguments to find a Sport
     * @example
     * // Get one Sport
     * const sport = await prisma.sport.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends SportFindFirstArgs>(args?: SelectSubset<T, SportFindFirstArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Sport that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SportFindFirstOrThrowArgs} args - Arguments to find a Sport
     * @example
     * // Get one Sport
     * const sport = await prisma.sport.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends SportFindFirstOrThrowArgs>(args?: SelectSubset<T, SportFindFirstOrThrowArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Sports that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SportFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Sports
     * const sports = await prisma.sport.findMany()
     * 
     * // Get first 10 Sports
     * const sports = await prisma.sport.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const sportWithIdOnly = await prisma.sport.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends SportFindManyArgs>(args?: SelectSubset<T, SportFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Sport.
     * @param {SportCreateArgs} args - Arguments to create a Sport.
     * @example
     * // Create one Sport
     * const Sport = await prisma.sport.create({
     *   data: {
     *     // ... data to create a Sport
     *   }
     * })
     * 
     */
    create<T extends SportCreateArgs>(args: SelectSubset<T, SportCreateArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Sports.
     * @param {SportCreateManyArgs} args - Arguments to create many Sports.
     * @example
     * // Create many Sports
     * const sport = await prisma.sport.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends SportCreateManyArgs>(args?: SelectSubset<T, SportCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Sports and returns the data saved in the database.
     * @param {SportCreateManyAndReturnArgs} args - Arguments to create many Sports.
     * @example
     * // Create many Sports
     * const sport = await prisma.sport.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Sports and only return the `id`
     * const sportWithIdOnly = await prisma.sport.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends SportCreateManyAndReturnArgs>(args?: SelectSubset<T, SportCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Sport.
     * @param {SportDeleteArgs} args - Arguments to delete one Sport.
     * @example
     * // Delete one Sport
     * const Sport = await prisma.sport.delete({
     *   where: {
     *     // ... filter to delete one Sport
     *   }
     * })
     * 
     */
    delete<T extends SportDeleteArgs>(args: SelectSubset<T, SportDeleteArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Sport.
     * @param {SportUpdateArgs} args - Arguments to update one Sport.
     * @example
     * // Update one Sport
     * const sport = await prisma.sport.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends SportUpdateArgs>(args: SelectSubset<T, SportUpdateArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Sports.
     * @param {SportDeleteManyArgs} args - Arguments to filter Sports to delete.
     * @example
     * // Delete a few Sports
     * const { count } = await prisma.sport.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends SportDeleteManyArgs>(args?: SelectSubset<T, SportDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Sports.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SportUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Sports
     * const sport = await prisma.sport.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends SportUpdateManyArgs>(args: SelectSubset<T, SportUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Sports and returns the data updated in the database.
     * @param {SportUpdateManyAndReturnArgs} args - Arguments to update many Sports.
     * @example
     * // Update many Sports
     * const sport = await prisma.sport.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Sports and only return the `id`
     * const sportWithIdOnly = await prisma.sport.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends SportUpdateManyAndReturnArgs>(args: SelectSubset<T, SportUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Sport.
     * @param {SportUpsertArgs} args - Arguments to update or create a Sport.
     * @example
     * // Update or create a Sport
     * const sport = await prisma.sport.upsert({
     *   create: {
     *     // ... data to create a Sport
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Sport we want to update
     *   }
     * })
     */
    upsert<T extends SportUpsertArgs>(args: SelectSubset<T, SportUpsertArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Sports.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SportCountArgs} args - Arguments to filter Sports to count.
     * @example
     * // Count the number of Sports
     * const count = await prisma.sport.count({
     *   where: {
     *     // ... the filter for the Sports we want to count
     *   }
     * })
    **/
    count<T extends SportCountArgs>(
      args?: Subset<T, SportCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], SportCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Sport.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SportAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends SportAggregateArgs>(args: Subset<T, SportAggregateArgs>): Prisma.PrismaPromise<GetSportAggregateType<T>>

    /**
     * Group by Sport.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SportGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends SportGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: SportGroupByArgs['orderBy'] }
        : { orderBy?: SportGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, SportGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetSportGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Sport model
   */
  readonly fields: SportFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Sport.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__SportClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    teams<T extends Sport$teamsArgs<ExtArgs> = {}>(args?: Subset<T, Sport$teamsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    games<T extends Sport$gamesArgs<ExtArgs> = {}>(args?: Subset<T, Sport$gamesArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Sport model
   */
  interface SportFieldRefs {
    readonly id: FieldRef<"Sport", 'String'>
    readonly key: FieldRef<"Sport", 'String'>
    readonly name: FieldRef<"Sport", 'String'>
    readonly createdAt: FieldRef<"Sport", 'DateTime'>
    readonly updatedAt: FieldRef<"Sport", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * Sport findUnique
   */
  export type SportFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
    /**
     * Filter, which Sport to fetch.
     */
    where: SportWhereUniqueInput
  }

  /**
   * Sport findUniqueOrThrow
   */
  export type SportFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
    /**
     * Filter, which Sport to fetch.
     */
    where: SportWhereUniqueInput
  }

  /**
   * Sport findFirst
   */
  export type SportFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
    /**
     * Filter, which Sport to fetch.
     */
    where?: SportWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sports to fetch.
     */
    orderBy?: SportOrderByWithRelationInput | SportOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Sports.
     */
    cursor?: SportWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sports from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sports.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Sports.
     */
    distinct?: SportScalarFieldEnum | SportScalarFieldEnum[]
  }

  /**
   * Sport findFirstOrThrow
   */
  export type SportFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
    /**
     * Filter, which Sport to fetch.
     */
    where?: SportWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sports to fetch.
     */
    orderBy?: SportOrderByWithRelationInput | SportOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Sports.
     */
    cursor?: SportWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sports from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sports.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Sports.
     */
    distinct?: SportScalarFieldEnum | SportScalarFieldEnum[]
  }

  /**
   * Sport findMany
   */
  export type SportFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
    /**
     * Filter, which Sports to fetch.
     */
    where?: SportWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sports to fetch.
     */
    orderBy?: SportOrderByWithRelationInput | SportOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Sports.
     */
    cursor?: SportWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sports from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sports.
     */
    skip?: number
    distinct?: SportScalarFieldEnum | SportScalarFieldEnum[]
  }

  /**
   * Sport create
   */
  export type SportCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
    /**
     * The data needed to create a Sport.
     */
    data: XOR<SportCreateInput, SportUncheckedCreateInput>
  }

  /**
   * Sport createMany
   */
  export type SportCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Sports.
     */
    data: SportCreateManyInput | SportCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Sport createManyAndReturn
   */
  export type SportCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * The data used to create many Sports.
     */
    data: SportCreateManyInput | SportCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Sport update
   */
  export type SportUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
    /**
     * The data needed to update a Sport.
     */
    data: XOR<SportUpdateInput, SportUncheckedUpdateInput>
    /**
     * Choose, which Sport to update.
     */
    where: SportWhereUniqueInput
  }

  /**
   * Sport updateMany
   */
  export type SportUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Sports.
     */
    data: XOR<SportUpdateManyMutationInput, SportUncheckedUpdateManyInput>
    /**
     * Filter which Sports to update
     */
    where?: SportWhereInput
    /**
     * Limit how many Sports to update.
     */
    limit?: number
  }

  /**
   * Sport updateManyAndReturn
   */
  export type SportUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * The data used to update Sports.
     */
    data: XOR<SportUpdateManyMutationInput, SportUncheckedUpdateManyInput>
    /**
     * Filter which Sports to update
     */
    where?: SportWhereInput
    /**
     * Limit how many Sports to update.
     */
    limit?: number
  }

  /**
   * Sport upsert
   */
  export type SportUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
    /**
     * The filter to search for the Sport to update in case it exists.
     */
    where: SportWhereUniqueInput
    /**
     * In case the Sport found by the `where` argument doesn't exist, create a new Sport with this data.
     */
    create: XOR<SportCreateInput, SportUncheckedCreateInput>
    /**
     * In case the Sport was found with the provided `where` argument, update it with this data.
     */
    update: XOR<SportUpdateInput, SportUncheckedUpdateInput>
  }

  /**
   * Sport delete
   */
  export type SportDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
    /**
     * Filter which Sport to delete.
     */
    where: SportWhereUniqueInput
  }

  /**
   * Sport deleteMany
   */
  export type SportDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Sports to delete
     */
    where?: SportWhereInput
    /**
     * Limit how many Sports to delete.
     */
    limit?: number
  }

  /**
   * Sport.teams
   */
  export type Sport$teamsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    where?: TeamWhereInput
    orderBy?: TeamOrderByWithRelationInput | TeamOrderByWithRelationInput[]
    cursor?: TeamWhereUniqueInput
    take?: number
    skip?: number
    distinct?: TeamScalarFieldEnum | TeamScalarFieldEnum[]
  }

  /**
   * Sport.games
   */
  export type Sport$gamesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    where?: GameWhereInput
    orderBy?: GameOrderByWithRelationInput | GameOrderByWithRelationInput[]
    cursor?: GameWhereUniqueInput
    take?: number
    skip?: number
    distinct?: GameScalarFieldEnum | GameScalarFieldEnum[]
  }

  /**
   * Sport without action
   */
  export type SportDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Sport
     */
    select?: SportSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Sport
     */
    omit?: SportOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SportInclude<ExtArgs> | null
  }


  /**
   * Model Team
   */

  export type AggregateTeam = {
    _count: TeamCountAggregateOutputType | null
    _min: TeamMinAggregateOutputType | null
    _max: TeamMaxAggregateOutputType | null
  }

  export type TeamMinAggregateOutputType = {
    id: string | null
    sportId: string | null
    name: string | null
    slug: string | null
    abbr: string | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type TeamMaxAggregateOutputType = {
    id: string | null
    sportId: string | null
    name: string | null
    slug: string | null
    abbr: string | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type TeamCountAggregateOutputType = {
    id: number
    sportId: number
    name: number
    slug: number
    abbr: number
    createdAt: number
    updatedAt: number
    _all: number
  }


  export type TeamMinAggregateInputType = {
    id?: true
    sportId?: true
    name?: true
    slug?: true
    abbr?: true
    createdAt?: true
    updatedAt?: true
  }

  export type TeamMaxAggregateInputType = {
    id?: true
    sportId?: true
    name?: true
    slug?: true
    abbr?: true
    createdAt?: true
    updatedAt?: true
  }

  export type TeamCountAggregateInputType = {
    id?: true
    sportId?: true
    name?: true
    slug?: true
    abbr?: true
    createdAt?: true
    updatedAt?: true
    _all?: true
  }

  export type TeamAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Team to aggregate.
     */
    where?: TeamWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Teams to fetch.
     */
    orderBy?: TeamOrderByWithRelationInput | TeamOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: TeamWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Teams from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Teams.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Teams
    **/
    _count?: true | TeamCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: TeamMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: TeamMaxAggregateInputType
  }

  export type GetTeamAggregateType<T extends TeamAggregateArgs> = {
        [P in keyof T & keyof AggregateTeam]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateTeam[P]>
      : GetScalarType<T[P], AggregateTeam[P]>
  }




  export type TeamGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TeamWhereInput
    orderBy?: TeamOrderByWithAggregationInput | TeamOrderByWithAggregationInput[]
    by: TeamScalarFieldEnum[] | TeamScalarFieldEnum
    having?: TeamScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: TeamCountAggregateInputType | true
    _min?: TeamMinAggregateInputType
    _max?: TeamMaxAggregateInputType
  }

  export type TeamGroupByOutputType = {
    id: string
    sportId: string
    name: string
    slug: string
    abbr: string | null
    createdAt: Date
    updatedAt: Date
    _count: TeamCountAggregateOutputType | null
    _min: TeamMinAggregateOutputType | null
    _max: TeamMaxAggregateOutputType | null
  }

  type GetTeamGroupByPayload<T extends TeamGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<TeamGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof TeamGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], TeamGroupByOutputType[P]>
            : GetScalarType<T[P], TeamGroupByOutputType[P]>
        }
      >
    >


  export type TeamSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    sportId?: boolean
    name?: boolean
    slug?: boolean
    abbr?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    sport?: boolean | SportDefaultArgs<ExtArgs>
    homeGames?: boolean | Team$homeGamesArgs<ExtArgs>
    awayGames?: boolean | Team$awayGamesArgs<ExtArgs>
    injuries?: boolean | Team$injuriesArgs<ExtArgs>
    profiles?: boolean | Team$profilesArgs<ExtArgs>
    _count?: boolean | TeamCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["team"]>

  export type TeamSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    sportId?: boolean
    name?: boolean
    slug?: boolean
    abbr?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    sport?: boolean | SportDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["team"]>

  export type TeamSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    sportId?: boolean
    name?: boolean
    slug?: boolean
    abbr?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    sport?: boolean | SportDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["team"]>

  export type TeamSelectScalar = {
    id?: boolean
    sportId?: boolean
    name?: boolean
    slug?: boolean
    abbr?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }

  export type TeamOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "sportId" | "name" | "slug" | "abbr" | "createdAt" | "updatedAt", ExtArgs["result"]["team"]>
  export type TeamInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    sport?: boolean | SportDefaultArgs<ExtArgs>
    homeGames?: boolean | Team$homeGamesArgs<ExtArgs>
    awayGames?: boolean | Team$awayGamesArgs<ExtArgs>
    injuries?: boolean | Team$injuriesArgs<ExtArgs>
    profiles?: boolean | Team$profilesArgs<ExtArgs>
    _count?: boolean | TeamCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type TeamIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    sport?: boolean | SportDefaultArgs<ExtArgs>
  }
  export type TeamIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    sport?: boolean | SportDefaultArgs<ExtArgs>
  }

  export type $TeamPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Team"
    objects: {
      sport: Prisma.$SportPayload<ExtArgs>
      homeGames: Prisma.$GamePayload<ExtArgs>[]
      awayGames: Prisma.$GamePayload<ExtArgs>[]
      injuries: Prisma.$InjuryPayload<ExtArgs>[]
      profiles: Prisma.$TeamProfileWeeklyPayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      sportId: string
      name: string
      slug: string
      abbr: string | null
      createdAt: Date
      updatedAt: Date
    }, ExtArgs["result"]["team"]>
    composites: {}
  }

  type TeamGetPayload<S extends boolean | null | undefined | TeamDefaultArgs> = $Result.GetResult<Prisma.$TeamPayload, S>

  type TeamCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<TeamFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: TeamCountAggregateInputType | true
    }

  export interface TeamDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Team'], meta: { name: 'Team' } }
    /**
     * Find zero or one Team that matches the filter.
     * @param {TeamFindUniqueArgs} args - Arguments to find a Team
     * @example
     * // Get one Team
     * const team = await prisma.team.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends TeamFindUniqueArgs>(args: SelectSubset<T, TeamFindUniqueArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Team that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {TeamFindUniqueOrThrowArgs} args - Arguments to find a Team
     * @example
     * // Get one Team
     * const team = await prisma.team.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends TeamFindUniqueOrThrowArgs>(args: SelectSubset<T, TeamFindUniqueOrThrowArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Team that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamFindFirstArgs} args - Arguments to find a Team
     * @example
     * // Get one Team
     * const team = await prisma.team.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends TeamFindFirstArgs>(args?: SelectSubset<T, TeamFindFirstArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Team that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamFindFirstOrThrowArgs} args - Arguments to find a Team
     * @example
     * // Get one Team
     * const team = await prisma.team.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends TeamFindFirstOrThrowArgs>(args?: SelectSubset<T, TeamFindFirstOrThrowArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Teams that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Teams
     * const teams = await prisma.team.findMany()
     * 
     * // Get first 10 Teams
     * const teams = await prisma.team.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const teamWithIdOnly = await prisma.team.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends TeamFindManyArgs>(args?: SelectSubset<T, TeamFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Team.
     * @param {TeamCreateArgs} args - Arguments to create a Team.
     * @example
     * // Create one Team
     * const Team = await prisma.team.create({
     *   data: {
     *     // ... data to create a Team
     *   }
     * })
     * 
     */
    create<T extends TeamCreateArgs>(args: SelectSubset<T, TeamCreateArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Teams.
     * @param {TeamCreateManyArgs} args - Arguments to create many Teams.
     * @example
     * // Create many Teams
     * const team = await prisma.team.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends TeamCreateManyArgs>(args?: SelectSubset<T, TeamCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Teams and returns the data saved in the database.
     * @param {TeamCreateManyAndReturnArgs} args - Arguments to create many Teams.
     * @example
     * // Create many Teams
     * const team = await prisma.team.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Teams and only return the `id`
     * const teamWithIdOnly = await prisma.team.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends TeamCreateManyAndReturnArgs>(args?: SelectSubset<T, TeamCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Team.
     * @param {TeamDeleteArgs} args - Arguments to delete one Team.
     * @example
     * // Delete one Team
     * const Team = await prisma.team.delete({
     *   where: {
     *     // ... filter to delete one Team
     *   }
     * })
     * 
     */
    delete<T extends TeamDeleteArgs>(args: SelectSubset<T, TeamDeleteArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Team.
     * @param {TeamUpdateArgs} args - Arguments to update one Team.
     * @example
     * // Update one Team
     * const team = await prisma.team.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends TeamUpdateArgs>(args: SelectSubset<T, TeamUpdateArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Teams.
     * @param {TeamDeleteManyArgs} args - Arguments to filter Teams to delete.
     * @example
     * // Delete a few Teams
     * const { count } = await prisma.team.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends TeamDeleteManyArgs>(args?: SelectSubset<T, TeamDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Teams.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Teams
     * const team = await prisma.team.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends TeamUpdateManyArgs>(args: SelectSubset<T, TeamUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Teams and returns the data updated in the database.
     * @param {TeamUpdateManyAndReturnArgs} args - Arguments to update many Teams.
     * @example
     * // Update many Teams
     * const team = await prisma.team.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Teams and only return the `id`
     * const teamWithIdOnly = await prisma.team.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends TeamUpdateManyAndReturnArgs>(args: SelectSubset<T, TeamUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Team.
     * @param {TeamUpsertArgs} args - Arguments to update or create a Team.
     * @example
     * // Update or create a Team
     * const team = await prisma.team.upsert({
     *   create: {
     *     // ... data to create a Team
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Team we want to update
     *   }
     * })
     */
    upsert<T extends TeamUpsertArgs>(args: SelectSubset<T, TeamUpsertArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Teams.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamCountArgs} args - Arguments to filter Teams to count.
     * @example
     * // Count the number of Teams
     * const count = await prisma.team.count({
     *   where: {
     *     // ... the filter for the Teams we want to count
     *   }
     * })
    **/
    count<T extends TeamCountArgs>(
      args?: Subset<T, TeamCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], TeamCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Team.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends TeamAggregateArgs>(args: Subset<T, TeamAggregateArgs>): Prisma.PrismaPromise<GetTeamAggregateType<T>>

    /**
     * Group by Team.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends TeamGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: TeamGroupByArgs['orderBy'] }
        : { orderBy?: TeamGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, TeamGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetTeamGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Team model
   */
  readonly fields: TeamFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Team.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__TeamClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    sport<T extends SportDefaultArgs<ExtArgs> = {}>(args?: Subset<T, SportDefaultArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    homeGames<T extends Team$homeGamesArgs<ExtArgs> = {}>(args?: Subset<T, Team$homeGamesArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    awayGames<T extends Team$awayGamesArgs<ExtArgs> = {}>(args?: Subset<T, Team$awayGamesArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    injuries<T extends Team$injuriesArgs<ExtArgs> = {}>(args?: Subset<T, Team$injuriesArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    profiles<T extends Team$profilesArgs<ExtArgs> = {}>(args?: Subset<T, Team$profilesArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Team model
   */
  interface TeamFieldRefs {
    readonly id: FieldRef<"Team", 'String'>
    readonly sportId: FieldRef<"Team", 'String'>
    readonly name: FieldRef<"Team", 'String'>
    readonly slug: FieldRef<"Team", 'String'>
    readonly abbr: FieldRef<"Team", 'String'>
    readonly createdAt: FieldRef<"Team", 'DateTime'>
    readonly updatedAt: FieldRef<"Team", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * Team findUnique
   */
  export type TeamFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    /**
     * Filter, which Team to fetch.
     */
    where: TeamWhereUniqueInput
  }

  /**
   * Team findUniqueOrThrow
   */
  export type TeamFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    /**
     * Filter, which Team to fetch.
     */
    where: TeamWhereUniqueInput
  }

  /**
   * Team findFirst
   */
  export type TeamFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    /**
     * Filter, which Team to fetch.
     */
    where?: TeamWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Teams to fetch.
     */
    orderBy?: TeamOrderByWithRelationInput | TeamOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Teams.
     */
    cursor?: TeamWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Teams from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Teams.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Teams.
     */
    distinct?: TeamScalarFieldEnum | TeamScalarFieldEnum[]
  }

  /**
   * Team findFirstOrThrow
   */
  export type TeamFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    /**
     * Filter, which Team to fetch.
     */
    where?: TeamWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Teams to fetch.
     */
    orderBy?: TeamOrderByWithRelationInput | TeamOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Teams.
     */
    cursor?: TeamWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Teams from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Teams.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Teams.
     */
    distinct?: TeamScalarFieldEnum | TeamScalarFieldEnum[]
  }

  /**
   * Team findMany
   */
  export type TeamFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    /**
     * Filter, which Teams to fetch.
     */
    where?: TeamWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Teams to fetch.
     */
    orderBy?: TeamOrderByWithRelationInput | TeamOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Teams.
     */
    cursor?: TeamWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Teams from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Teams.
     */
    skip?: number
    distinct?: TeamScalarFieldEnum | TeamScalarFieldEnum[]
  }

  /**
   * Team create
   */
  export type TeamCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    /**
     * The data needed to create a Team.
     */
    data: XOR<TeamCreateInput, TeamUncheckedCreateInput>
  }

  /**
   * Team createMany
   */
  export type TeamCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Teams.
     */
    data: TeamCreateManyInput | TeamCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Team createManyAndReturn
   */
  export type TeamCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * The data used to create many Teams.
     */
    data: TeamCreateManyInput | TeamCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Team update
   */
  export type TeamUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    /**
     * The data needed to update a Team.
     */
    data: XOR<TeamUpdateInput, TeamUncheckedUpdateInput>
    /**
     * Choose, which Team to update.
     */
    where: TeamWhereUniqueInput
  }

  /**
   * Team updateMany
   */
  export type TeamUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Teams.
     */
    data: XOR<TeamUpdateManyMutationInput, TeamUncheckedUpdateManyInput>
    /**
     * Filter which Teams to update
     */
    where?: TeamWhereInput
    /**
     * Limit how many Teams to update.
     */
    limit?: number
  }

  /**
   * Team updateManyAndReturn
   */
  export type TeamUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * The data used to update Teams.
     */
    data: XOR<TeamUpdateManyMutationInput, TeamUncheckedUpdateManyInput>
    /**
     * Filter which Teams to update
     */
    where?: TeamWhereInput
    /**
     * Limit how many Teams to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Team upsert
   */
  export type TeamUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    /**
     * The filter to search for the Team to update in case it exists.
     */
    where: TeamWhereUniqueInput
    /**
     * In case the Team found by the `where` argument doesn't exist, create a new Team with this data.
     */
    create: XOR<TeamCreateInput, TeamUncheckedCreateInput>
    /**
     * In case the Team was found with the provided `where` argument, update it with this data.
     */
    update: XOR<TeamUpdateInput, TeamUncheckedUpdateInput>
  }

  /**
   * Team delete
   */
  export type TeamDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
    /**
     * Filter which Team to delete.
     */
    where: TeamWhereUniqueInput
  }

  /**
   * Team deleteMany
   */
  export type TeamDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Teams to delete
     */
    where?: TeamWhereInput
    /**
     * Limit how many Teams to delete.
     */
    limit?: number
  }

  /**
   * Team.homeGames
   */
  export type Team$homeGamesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    where?: GameWhereInput
    orderBy?: GameOrderByWithRelationInput | GameOrderByWithRelationInput[]
    cursor?: GameWhereUniqueInput
    take?: number
    skip?: number
    distinct?: GameScalarFieldEnum | GameScalarFieldEnum[]
  }

  /**
   * Team.awayGames
   */
  export type Team$awayGamesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    where?: GameWhereInput
    orderBy?: GameOrderByWithRelationInput | GameOrderByWithRelationInput[]
    cursor?: GameWhereUniqueInput
    take?: number
    skip?: number
    distinct?: GameScalarFieldEnum | GameScalarFieldEnum[]
  }

  /**
   * Team.injuries
   */
  export type Team$injuriesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    where?: InjuryWhereInput
    orderBy?: InjuryOrderByWithRelationInput | InjuryOrderByWithRelationInput[]
    cursor?: InjuryWhereUniqueInput
    take?: number
    skip?: number
    distinct?: InjuryScalarFieldEnum | InjuryScalarFieldEnum[]
  }

  /**
   * Team.profiles
   */
  export type Team$profilesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    where?: TeamProfileWeeklyWhereInput
    orderBy?: TeamProfileWeeklyOrderByWithRelationInput | TeamProfileWeeklyOrderByWithRelationInput[]
    cursor?: TeamProfileWeeklyWhereUniqueInput
    take?: number
    skip?: number
    distinct?: TeamProfileWeeklyScalarFieldEnum | TeamProfileWeeklyScalarFieldEnum[]
  }

  /**
   * Team without action
   */
  export type TeamDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Team
     */
    select?: TeamSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Team
     */
    omit?: TeamOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamInclude<ExtArgs> | null
  }


  /**
   * Model Game
   */

  export type AggregateGame = {
    _count: GameCountAggregateOutputType | null
    _min: GameMinAggregateOutputType | null
    _max: GameMaxAggregateOutputType | null
  }

  export type GameMinAggregateOutputType = {
    id: string | null
    sportId: string | null
    date: Date | null
    slug: string | null
    homeTeamId: string | null
    awayTeamId: string | null
    startTime: Date | null
    venue: string | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type GameMaxAggregateOutputType = {
    id: string | null
    sportId: string | null
    date: Date | null
    slug: string | null
    homeTeamId: string | null
    awayTeamId: string | null
    startTime: Date | null
    venue: string | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type GameCountAggregateOutputType = {
    id: number
    sportId: number
    date: number
    slug: number
    homeTeamId: number
    awayTeamId: number
    startTime: number
    venue: number
    createdAt: number
    updatedAt: number
    _all: number
  }


  export type GameMinAggregateInputType = {
    id?: true
    sportId?: true
    date?: true
    slug?: true
    homeTeamId?: true
    awayTeamId?: true
    startTime?: true
    venue?: true
    createdAt?: true
    updatedAt?: true
  }

  export type GameMaxAggregateInputType = {
    id?: true
    sportId?: true
    date?: true
    slug?: true
    homeTeamId?: true
    awayTeamId?: true
    startTime?: true
    venue?: true
    createdAt?: true
    updatedAt?: true
  }

  export type GameCountAggregateInputType = {
    id?: true
    sportId?: true
    date?: true
    slug?: true
    homeTeamId?: true
    awayTeamId?: true
    startTime?: true
    venue?: true
    createdAt?: true
    updatedAt?: true
    _all?: true
  }

  export type GameAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Game to aggregate.
     */
    where?: GameWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Games to fetch.
     */
    orderBy?: GameOrderByWithRelationInput | GameOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: GameWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Games from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Games.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Games
    **/
    _count?: true | GameCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: GameMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: GameMaxAggregateInputType
  }

  export type GetGameAggregateType<T extends GameAggregateArgs> = {
        [P in keyof T & keyof AggregateGame]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateGame[P]>
      : GetScalarType<T[P], AggregateGame[P]>
  }




  export type GameGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: GameWhereInput
    orderBy?: GameOrderByWithAggregationInput | GameOrderByWithAggregationInput[]
    by: GameScalarFieldEnum[] | GameScalarFieldEnum
    having?: GameScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: GameCountAggregateInputType | true
    _min?: GameMinAggregateInputType
    _max?: GameMaxAggregateInputType
  }

  export type GameGroupByOutputType = {
    id: string
    sportId: string
    date: Date
    slug: string
    homeTeamId: string
    awayTeamId: string
    startTime: Date | null
    venue: string | null
    createdAt: Date
    updatedAt: Date
    _count: GameCountAggregateOutputType | null
    _min: GameMinAggregateOutputType | null
    _max: GameMaxAggregateOutputType | null
  }

  type GetGameGroupByPayload<T extends GameGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<GameGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof GameGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], GameGroupByOutputType[P]>
            : GetScalarType<T[P], GameGroupByOutputType[P]>
        }
      >
    >


  export type GameSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    sportId?: boolean
    date?: boolean
    slug?: boolean
    homeTeamId?: boolean
    awayTeamId?: boolean
    startTime?: boolean
    venue?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    sport?: boolean | SportDefaultArgs<ExtArgs>
    homeTeam?: boolean | TeamDefaultArgs<ExtArgs>
    awayTeam?: boolean | TeamDefaultArgs<ExtArgs>
    market?: boolean | Game$marketArgs<ExtArgs>
    model?: boolean | Game$modelArgs<ExtArgs>
    writeup?: boolean | Game$writeupArgs<ExtArgs>
  }, ExtArgs["result"]["game"]>

  export type GameSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    sportId?: boolean
    date?: boolean
    slug?: boolean
    homeTeamId?: boolean
    awayTeamId?: boolean
    startTime?: boolean
    venue?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    sport?: boolean | SportDefaultArgs<ExtArgs>
    homeTeam?: boolean | TeamDefaultArgs<ExtArgs>
    awayTeam?: boolean | TeamDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["game"]>

  export type GameSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    sportId?: boolean
    date?: boolean
    slug?: boolean
    homeTeamId?: boolean
    awayTeamId?: boolean
    startTime?: boolean
    venue?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    sport?: boolean | SportDefaultArgs<ExtArgs>
    homeTeam?: boolean | TeamDefaultArgs<ExtArgs>
    awayTeam?: boolean | TeamDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["game"]>

  export type GameSelectScalar = {
    id?: boolean
    sportId?: boolean
    date?: boolean
    slug?: boolean
    homeTeamId?: boolean
    awayTeamId?: boolean
    startTime?: boolean
    venue?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }

  export type GameOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "sportId" | "date" | "slug" | "homeTeamId" | "awayTeamId" | "startTime" | "venue" | "createdAt" | "updatedAt", ExtArgs["result"]["game"]>
  export type GameInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    sport?: boolean | SportDefaultArgs<ExtArgs>
    homeTeam?: boolean | TeamDefaultArgs<ExtArgs>
    awayTeam?: boolean | TeamDefaultArgs<ExtArgs>
    market?: boolean | Game$marketArgs<ExtArgs>
    model?: boolean | Game$modelArgs<ExtArgs>
    writeup?: boolean | Game$writeupArgs<ExtArgs>
  }
  export type GameIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    sport?: boolean | SportDefaultArgs<ExtArgs>
    homeTeam?: boolean | TeamDefaultArgs<ExtArgs>
    awayTeam?: boolean | TeamDefaultArgs<ExtArgs>
  }
  export type GameIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    sport?: boolean | SportDefaultArgs<ExtArgs>
    homeTeam?: boolean | TeamDefaultArgs<ExtArgs>
    awayTeam?: boolean | TeamDefaultArgs<ExtArgs>
  }

  export type $GamePayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Game"
    objects: {
      sport: Prisma.$SportPayload<ExtArgs>
      homeTeam: Prisma.$TeamPayload<ExtArgs>
      awayTeam: Prisma.$TeamPayload<ExtArgs>
      market: Prisma.$MarketSnapshotPayload<ExtArgs> | null
      model: Prisma.$ModelProjectionPayload<ExtArgs> | null
      writeup: Prisma.$WriteupPayload<ExtArgs> | null
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      sportId: string
      date: Date
      slug: string
      homeTeamId: string
      awayTeamId: string
      startTime: Date | null
      venue: string | null
      createdAt: Date
      updatedAt: Date
    }, ExtArgs["result"]["game"]>
    composites: {}
  }

  type GameGetPayload<S extends boolean | null | undefined | GameDefaultArgs> = $Result.GetResult<Prisma.$GamePayload, S>

  type GameCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<GameFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: GameCountAggregateInputType | true
    }

  export interface GameDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Game'], meta: { name: 'Game' } }
    /**
     * Find zero or one Game that matches the filter.
     * @param {GameFindUniqueArgs} args - Arguments to find a Game
     * @example
     * // Get one Game
     * const game = await prisma.game.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends GameFindUniqueArgs>(args: SelectSubset<T, GameFindUniqueArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Game that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {GameFindUniqueOrThrowArgs} args - Arguments to find a Game
     * @example
     * // Get one Game
     * const game = await prisma.game.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends GameFindUniqueOrThrowArgs>(args: SelectSubset<T, GameFindUniqueOrThrowArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Game that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {GameFindFirstArgs} args - Arguments to find a Game
     * @example
     * // Get one Game
     * const game = await prisma.game.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends GameFindFirstArgs>(args?: SelectSubset<T, GameFindFirstArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Game that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {GameFindFirstOrThrowArgs} args - Arguments to find a Game
     * @example
     * // Get one Game
     * const game = await prisma.game.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends GameFindFirstOrThrowArgs>(args?: SelectSubset<T, GameFindFirstOrThrowArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Games that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {GameFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Games
     * const games = await prisma.game.findMany()
     * 
     * // Get first 10 Games
     * const games = await prisma.game.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const gameWithIdOnly = await prisma.game.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends GameFindManyArgs>(args?: SelectSubset<T, GameFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Game.
     * @param {GameCreateArgs} args - Arguments to create a Game.
     * @example
     * // Create one Game
     * const Game = await prisma.game.create({
     *   data: {
     *     // ... data to create a Game
     *   }
     * })
     * 
     */
    create<T extends GameCreateArgs>(args: SelectSubset<T, GameCreateArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Games.
     * @param {GameCreateManyArgs} args - Arguments to create many Games.
     * @example
     * // Create many Games
     * const game = await prisma.game.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends GameCreateManyArgs>(args?: SelectSubset<T, GameCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Games and returns the data saved in the database.
     * @param {GameCreateManyAndReturnArgs} args - Arguments to create many Games.
     * @example
     * // Create many Games
     * const game = await prisma.game.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Games and only return the `id`
     * const gameWithIdOnly = await prisma.game.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends GameCreateManyAndReturnArgs>(args?: SelectSubset<T, GameCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Game.
     * @param {GameDeleteArgs} args - Arguments to delete one Game.
     * @example
     * // Delete one Game
     * const Game = await prisma.game.delete({
     *   where: {
     *     // ... filter to delete one Game
     *   }
     * })
     * 
     */
    delete<T extends GameDeleteArgs>(args: SelectSubset<T, GameDeleteArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Game.
     * @param {GameUpdateArgs} args - Arguments to update one Game.
     * @example
     * // Update one Game
     * const game = await prisma.game.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends GameUpdateArgs>(args: SelectSubset<T, GameUpdateArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Games.
     * @param {GameDeleteManyArgs} args - Arguments to filter Games to delete.
     * @example
     * // Delete a few Games
     * const { count } = await prisma.game.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends GameDeleteManyArgs>(args?: SelectSubset<T, GameDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Games.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {GameUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Games
     * const game = await prisma.game.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends GameUpdateManyArgs>(args: SelectSubset<T, GameUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Games and returns the data updated in the database.
     * @param {GameUpdateManyAndReturnArgs} args - Arguments to update many Games.
     * @example
     * // Update many Games
     * const game = await prisma.game.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Games and only return the `id`
     * const gameWithIdOnly = await prisma.game.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends GameUpdateManyAndReturnArgs>(args: SelectSubset<T, GameUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Game.
     * @param {GameUpsertArgs} args - Arguments to update or create a Game.
     * @example
     * // Update or create a Game
     * const game = await prisma.game.upsert({
     *   create: {
     *     // ... data to create a Game
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Game we want to update
     *   }
     * })
     */
    upsert<T extends GameUpsertArgs>(args: SelectSubset<T, GameUpsertArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Games.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {GameCountArgs} args - Arguments to filter Games to count.
     * @example
     * // Count the number of Games
     * const count = await prisma.game.count({
     *   where: {
     *     // ... the filter for the Games we want to count
     *   }
     * })
    **/
    count<T extends GameCountArgs>(
      args?: Subset<T, GameCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], GameCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Game.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {GameAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends GameAggregateArgs>(args: Subset<T, GameAggregateArgs>): Prisma.PrismaPromise<GetGameAggregateType<T>>

    /**
     * Group by Game.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {GameGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends GameGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: GameGroupByArgs['orderBy'] }
        : { orderBy?: GameGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, GameGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetGameGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Game model
   */
  readonly fields: GameFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Game.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__GameClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    sport<T extends SportDefaultArgs<ExtArgs> = {}>(args?: Subset<T, SportDefaultArgs<ExtArgs>>): Prisma__SportClient<$Result.GetResult<Prisma.$SportPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    homeTeam<T extends TeamDefaultArgs<ExtArgs> = {}>(args?: Subset<T, TeamDefaultArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    awayTeam<T extends TeamDefaultArgs<ExtArgs> = {}>(args?: Subset<T, TeamDefaultArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    market<T extends Game$marketArgs<ExtArgs> = {}>(args?: Subset<T, Game$marketArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>
    model<T extends Game$modelArgs<ExtArgs> = {}>(args?: Subset<T, Game$modelArgs<ExtArgs>>): Prisma__ModelProjectionClient<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>
    writeup<T extends Game$writeupArgs<ExtArgs> = {}>(args?: Subset<T, Game$writeupArgs<ExtArgs>>): Prisma__WriteupClient<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Game model
   */
  interface GameFieldRefs {
    readonly id: FieldRef<"Game", 'String'>
    readonly sportId: FieldRef<"Game", 'String'>
    readonly date: FieldRef<"Game", 'DateTime'>
    readonly slug: FieldRef<"Game", 'String'>
    readonly homeTeamId: FieldRef<"Game", 'String'>
    readonly awayTeamId: FieldRef<"Game", 'String'>
    readonly startTime: FieldRef<"Game", 'DateTime'>
    readonly venue: FieldRef<"Game", 'String'>
    readonly createdAt: FieldRef<"Game", 'DateTime'>
    readonly updatedAt: FieldRef<"Game", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * Game findUnique
   */
  export type GameFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    /**
     * Filter, which Game to fetch.
     */
    where: GameWhereUniqueInput
  }

  /**
   * Game findUniqueOrThrow
   */
  export type GameFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    /**
     * Filter, which Game to fetch.
     */
    where: GameWhereUniqueInput
  }

  /**
   * Game findFirst
   */
  export type GameFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    /**
     * Filter, which Game to fetch.
     */
    where?: GameWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Games to fetch.
     */
    orderBy?: GameOrderByWithRelationInput | GameOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Games.
     */
    cursor?: GameWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Games from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Games.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Games.
     */
    distinct?: GameScalarFieldEnum | GameScalarFieldEnum[]
  }

  /**
   * Game findFirstOrThrow
   */
  export type GameFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    /**
     * Filter, which Game to fetch.
     */
    where?: GameWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Games to fetch.
     */
    orderBy?: GameOrderByWithRelationInput | GameOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Games.
     */
    cursor?: GameWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Games from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Games.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Games.
     */
    distinct?: GameScalarFieldEnum | GameScalarFieldEnum[]
  }

  /**
   * Game findMany
   */
  export type GameFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    /**
     * Filter, which Games to fetch.
     */
    where?: GameWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Games to fetch.
     */
    orderBy?: GameOrderByWithRelationInput | GameOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Games.
     */
    cursor?: GameWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Games from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Games.
     */
    skip?: number
    distinct?: GameScalarFieldEnum | GameScalarFieldEnum[]
  }

  /**
   * Game create
   */
  export type GameCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    /**
     * The data needed to create a Game.
     */
    data: XOR<GameCreateInput, GameUncheckedCreateInput>
  }

  /**
   * Game createMany
   */
  export type GameCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Games.
     */
    data: GameCreateManyInput | GameCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Game createManyAndReturn
   */
  export type GameCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * The data used to create many Games.
     */
    data: GameCreateManyInput | GameCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Game update
   */
  export type GameUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    /**
     * The data needed to update a Game.
     */
    data: XOR<GameUpdateInput, GameUncheckedUpdateInput>
    /**
     * Choose, which Game to update.
     */
    where: GameWhereUniqueInput
  }

  /**
   * Game updateMany
   */
  export type GameUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Games.
     */
    data: XOR<GameUpdateManyMutationInput, GameUncheckedUpdateManyInput>
    /**
     * Filter which Games to update
     */
    where?: GameWhereInput
    /**
     * Limit how many Games to update.
     */
    limit?: number
  }

  /**
   * Game updateManyAndReturn
   */
  export type GameUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * The data used to update Games.
     */
    data: XOR<GameUpdateManyMutationInput, GameUncheckedUpdateManyInput>
    /**
     * Filter which Games to update
     */
    where?: GameWhereInput
    /**
     * Limit how many Games to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Game upsert
   */
  export type GameUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    /**
     * The filter to search for the Game to update in case it exists.
     */
    where: GameWhereUniqueInput
    /**
     * In case the Game found by the `where` argument doesn't exist, create a new Game with this data.
     */
    create: XOR<GameCreateInput, GameUncheckedCreateInput>
    /**
     * In case the Game was found with the provided `where` argument, update it with this data.
     */
    update: XOR<GameUpdateInput, GameUncheckedUpdateInput>
  }

  /**
   * Game delete
   */
  export type GameDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
    /**
     * Filter which Game to delete.
     */
    where: GameWhereUniqueInput
  }

  /**
   * Game deleteMany
   */
  export type GameDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Games to delete
     */
    where?: GameWhereInput
    /**
     * Limit how many Games to delete.
     */
    limit?: number
  }

  /**
   * Game.market
   */
  export type Game$marketArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    where?: MarketSnapshotWhereInput
  }

  /**
   * Game.model
   */
  export type Game$modelArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    where?: ModelProjectionWhereInput
  }

  /**
   * Game.writeup
   */
  export type Game$writeupArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    where?: WriteupWhereInput
  }

  /**
   * Game without action
   */
  export type GameDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Game
     */
    select?: GameSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Game
     */
    omit?: GameOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: GameInclude<ExtArgs> | null
  }


  /**
   * Model MarketSnapshot
   */

  export type AggregateMarketSnapshot = {
    _count: MarketSnapshotCountAggregateOutputType | null
    _avg: MarketSnapshotAvgAggregateOutputType | null
    _sum: MarketSnapshotSumAggregateOutputType | null
    _min: MarketSnapshotMinAggregateOutputType | null
    _max: MarketSnapshotMaxAggregateOutputType | null
  }

  export type MarketSnapshotAvgAggregateOutputType = {
    openSpreadHome: number | null
    currentSpreadHome: number | null
    openTotal: number | null
    currentTotal: number | null
    bestSpreadHome: number | null
    bestTotal: number | null
    spreadDispersion: number | null
    totalDispersion: number | null
  }

  export type MarketSnapshotSumAggregateOutputType = {
    openSpreadHome: number | null
    currentSpreadHome: number | null
    openTotal: number | null
    currentTotal: number | null
    bestSpreadHome: number | null
    bestTotal: number | null
    spreadDispersion: number | null
    totalDispersion: number | null
  }

  export type MarketSnapshotMinAggregateOutputType = {
    id: string | null
    gameId: string | null
    capturedAt: Date | null
    openSpreadHome: number | null
    currentSpreadHome: number | null
    openTotal: number | null
    currentTotal: number | null
    bestSpreadHome: number | null
    bestSpreadBook: string | null
    bestTotal: number | null
    bestTotalBook: string | null
    spreadDispersion: number | null
    totalDispersion: number | null
  }

  export type MarketSnapshotMaxAggregateOutputType = {
    id: string | null
    gameId: string | null
    capturedAt: Date | null
    openSpreadHome: number | null
    currentSpreadHome: number | null
    openTotal: number | null
    currentTotal: number | null
    bestSpreadHome: number | null
    bestSpreadBook: string | null
    bestTotal: number | null
    bestTotalBook: string | null
    spreadDispersion: number | null
    totalDispersion: number | null
  }

  export type MarketSnapshotCountAggregateOutputType = {
    id: number
    gameId: number
    capturedAt: number
    openSpreadHome: number
    currentSpreadHome: number
    openTotal: number
    currentTotal: number
    bestSpreadHome: number
    bestSpreadBook: number
    bestTotal: number
    bestTotalBook: number
    spreadDispersion: number
    totalDispersion: number
    _all: number
  }


  export type MarketSnapshotAvgAggregateInputType = {
    openSpreadHome?: true
    currentSpreadHome?: true
    openTotal?: true
    currentTotal?: true
    bestSpreadHome?: true
    bestTotal?: true
    spreadDispersion?: true
    totalDispersion?: true
  }

  export type MarketSnapshotSumAggregateInputType = {
    openSpreadHome?: true
    currentSpreadHome?: true
    openTotal?: true
    currentTotal?: true
    bestSpreadHome?: true
    bestTotal?: true
    spreadDispersion?: true
    totalDispersion?: true
  }

  export type MarketSnapshotMinAggregateInputType = {
    id?: true
    gameId?: true
    capturedAt?: true
    openSpreadHome?: true
    currentSpreadHome?: true
    openTotal?: true
    currentTotal?: true
    bestSpreadHome?: true
    bestSpreadBook?: true
    bestTotal?: true
    bestTotalBook?: true
    spreadDispersion?: true
    totalDispersion?: true
  }

  export type MarketSnapshotMaxAggregateInputType = {
    id?: true
    gameId?: true
    capturedAt?: true
    openSpreadHome?: true
    currentSpreadHome?: true
    openTotal?: true
    currentTotal?: true
    bestSpreadHome?: true
    bestSpreadBook?: true
    bestTotal?: true
    bestTotalBook?: true
    spreadDispersion?: true
    totalDispersion?: true
  }

  export type MarketSnapshotCountAggregateInputType = {
    id?: true
    gameId?: true
    capturedAt?: true
    openSpreadHome?: true
    currentSpreadHome?: true
    openTotal?: true
    currentTotal?: true
    bestSpreadHome?: true
    bestSpreadBook?: true
    bestTotal?: true
    bestTotalBook?: true
    spreadDispersion?: true
    totalDispersion?: true
    _all?: true
  }

  export type MarketSnapshotAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which MarketSnapshot to aggregate.
     */
    where?: MarketSnapshotWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of MarketSnapshots to fetch.
     */
    orderBy?: MarketSnapshotOrderByWithRelationInput | MarketSnapshotOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: MarketSnapshotWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` MarketSnapshots from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` MarketSnapshots.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned MarketSnapshots
    **/
    _count?: true | MarketSnapshotCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to average
    **/
    _avg?: MarketSnapshotAvgAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to sum
    **/
    _sum?: MarketSnapshotSumAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: MarketSnapshotMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: MarketSnapshotMaxAggregateInputType
  }

  export type GetMarketSnapshotAggregateType<T extends MarketSnapshotAggregateArgs> = {
        [P in keyof T & keyof AggregateMarketSnapshot]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateMarketSnapshot[P]>
      : GetScalarType<T[P], AggregateMarketSnapshot[P]>
  }




  export type MarketSnapshotGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: MarketSnapshotWhereInput
    orderBy?: MarketSnapshotOrderByWithAggregationInput | MarketSnapshotOrderByWithAggregationInput[]
    by: MarketSnapshotScalarFieldEnum[] | MarketSnapshotScalarFieldEnum
    having?: MarketSnapshotScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: MarketSnapshotCountAggregateInputType | true
    _avg?: MarketSnapshotAvgAggregateInputType
    _sum?: MarketSnapshotSumAggregateInputType
    _min?: MarketSnapshotMinAggregateInputType
    _max?: MarketSnapshotMaxAggregateInputType
  }

  export type MarketSnapshotGroupByOutputType = {
    id: string
    gameId: string
    capturedAt: Date
    openSpreadHome: number | null
    currentSpreadHome: number | null
    openTotal: number | null
    currentTotal: number | null
    bestSpreadHome: number | null
    bestSpreadBook: string | null
    bestTotal: number | null
    bestTotalBook: string | null
    spreadDispersion: number | null
    totalDispersion: number | null
    _count: MarketSnapshotCountAggregateOutputType | null
    _avg: MarketSnapshotAvgAggregateOutputType | null
    _sum: MarketSnapshotSumAggregateOutputType | null
    _min: MarketSnapshotMinAggregateOutputType | null
    _max: MarketSnapshotMaxAggregateOutputType | null
  }

  type GetMarketSnapshotGroupByPayload<T extends MarketSnapshotGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<MarketSnapshotGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof MarketSnapshotGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], MarketSnapshotGroupByOutputType[P]>
            : GetScalarType<T[P], MarketSnapshotGroupByOutputType[P]>
        }
      >
    >


  export type MarketSnapshotSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    gameId?: boolean
    capturedAt?: boolean
    openSpreadHome?: boolean
    currentSpreadHome?: boolean
    openTotal?: boolean
    currentTotal?: boolean
    bestSpreadHome?: boolean
    bestSpreadBook?: boolean
    bestTotal?: boolean
    bestTotalBook?: boolean
    spreadDispersion?: boolean
    totalDispersion?: boolean
    bookLines?: boolean | MarketSnapshot$bookLinesArgs<ExtArgs>
    game?: boolean | GameDefaultArgs<ExtArgs>
    _count?: boolean | MarketSnapshotCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["marketSnapshot"]>

  export type MarketSnapshotSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    gameId?: boolean
    capturedAt?: boolean
    openSpreadHome?: boolean
    currentSpreadHome?: boolean
    openTotal?: boolean
    currentTotal?: boolean
    bestSpreadHome?: boolean
    bestSpreadBook?: boolean
    bestTotal?: boolean
    bestTotalBook?: boolean
    spreadDispersion?: boolean
    totalDispersion?: boolean
    game?: boolean | GameDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["marketSnapshot"]>

  export type MarketSnapshotSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    gameId?: boolean
    capturedAt?: boolean
    openSpreadHome?: boolean
    currentSpreadHome?: boolean
    openTotal?: boolean
    currentTotal?: boolean
    bestSpreadHome?: boolean
    bestSpreadBook?: boolean
    bestTotal?: boolean
    bestTotalBook?: boolean
    spreadDispersion?: boolean
    totalDispersion?: boolean
    game?: boolean | GameDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["marketSnapshot"]>

  export type MarketSnapshotSelectScalar = {
    id?: boolean
    gameId?: boolean
    capturedAt?: boolean
    openSpreadHome?: boolean
    currentSpreadHome?: boolean
    openTotal?: boolean
    currentTotal?: boolean
    bestSpreadHome?: boolean
    bestSpreadBook?: boolean
    bestTotal?: boolean
    bestTotalBook?: boolean
    spreadDispersion?: boolean
    totalDispersion?: boolean
  }

  export type MarketSnapshotOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "gameId" | "capturedAt" | "openSpreadHome" | "currentSpreadHome" | "openTotal" | "currentTotal" | "bestSpreadHome" | "bestSpreadBook" | "bestTotal" | "bestTotalBook" | "spreadDispersion" | "totalDispersion", ExtArgs["result"]["marketSnapshot"]>
  export type MarketSnapshotInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    bookLines?: boolean | MarketSnapshot$bookLinesArgs<ExtArgs>
    game?: boolean | GameDefaultArgs<ExtArgs>
    _count?: boolean | MarketSnapshotCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type MarketSnapshotIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    game?: boolean | GameDefaultArgs<ExtArgs>
  }
  export type MarketSnapshotIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    game?: boolean | GameDefaultArgs<ExtArgs>
  }

  export type $MarketSnapshotPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "MarketSnapshot"
    objects: {
      bookLines: Prisma.$BookLinePayload<ExtArgs>[]
      game: Prisma.$GamePayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      gameId: string
      capturedAt: Date
      openSpreadHome: number | null
      currentSpreadHome: number | null
      openTotal: number | null
      currentTotal: number | null
      bestSpreadHome: number | null
      bestSpreadBook: string | null
      bestTotal: number | null
      bestTotalBook: string | null
      spreadDispersion: number | null
      totalDispersion: number | null
    }, ExtArgs["result"]["marketSnapshot"]>
    composites: {}
  }

  type MarketSnapshotGetPayload<S extends boolean | null | undefined | MarketSnapshotDefaultArgs> = $Result.GetResult<Prisma.$MarketSnapshotPayload, S>

  type MarketSnapshotCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<MarketSnapshotFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: MarketSnapshotCountAggregateInputType | true
    }

  export interface MarketSnapshotDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['MarketSnapshot'], meta: { name: 'MarketSnapshot' } }
    /**
     * Find zero or one MarketSnapshot that matches the filter.
     * @param {MarketSnapshotFindUniqueArgs} args - Arguments to find a MarketSnapshot
     * @example
     * // Get one MarketSnapshot
     * const marketSnapshot = await prisma.marketSnapshot.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends MarketSnapshotFindUniqueArgs>(args: SelectSubset<T, MarketSnapshotFindUniqueArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one MarketSnapshot that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {MarketSnapshotFindUniqueOrThrowArgs} args - Arguments to find a MarketSnapshot
     * @example
     * // Get one MarketSnapshot
     * const marketSnapshot = await prisma.marketSnapshot.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends MarketSnapshotFindUniqueOrThrowArgs>(args: SelectSubset<T, MarketSnapshotFindUniqueOrThrowArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first MarketSnapshot that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MarketSnapshotFindFirstArgs} args - Arguments to find a MarketSnapshot
     * @example
     * // Get one MarketSnapshot
     * const marketSnapshot = await prisma.marketSnapshot.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends MarketSnapshotFindFirstArgs>(args?: SelectSubset<T, MarketSnapshotFindFirstArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first MarketSnapshot that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MarketSnapshotFindFirstOrThrowArgs} args - Arguments to find a MarketSnapshot
     * @example
     * // Get one MarketSnapshot
     * const marketSnapshot = await prisma.marketSnapshot.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends MarketSnapshotFindFirstOrThrowArgs>(args?: SelectSubset<T, MarketSnapshotFindFirstOrThrowArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more MarketSnapshots that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MarketSnapshotFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all MarketSnapshots
     * const marketSnapshots = await prisma.marketSnapshot.findMany()
     * 
     * // Get first 10 MarketSnapshots
     * const marketSnapshots = await prisma.marketSnapshot.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const marketSnapshotWithIdOnly = await prisma.marketSnapshot.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends MarketSnapshotFindManyArgs>(args?: SelectSubset<T, MarketSnapshotFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a MarketSnapshot.
     * @param {MarketSnapshotCreateArgs} args - Arguments to create a MarketSnapshot.
     * @example
     * // Create one MarketSnapshot
     * const MarketSnapshot = await prisma.marketSnapshot.create({
     *   data: {
     *     // ... data to create a MarketSnapshot
     *   }
     * })
     * 
     */
    create<T extends MarketSnapshotCreateArgs>(args: SelectSubset<T, MarketSnapshotCreateArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many MarketSnapshots.
     * @param {MarketSnapshotCreateManyArgs} args - Arguments to create many MarketSnapshots.
     * @example
     * // Create many MarketSnapshots
     * const marketSnapshot = await prisma.marketSnapshot.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends MarketSnapshotCreateManyArgs>(args?: SelectSubset<T, MarketSnapshotCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many MarketSnapshots and returns the data saved in the database.
     * @param {MarketSnapshotCreateManyAndReturnArgs} args - Arguments to create many MarketSnapshots.
     * @example
     * // Create many MarketSnapshots
     * const marketSnapshot = await prisma.marketSnapshot.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many MarketSnapshots and only return the `id`
     * const marketSnapshotWithIdOnly = await prisma.marketSnapshot.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends MarketSnapshotCreateManyAndReturnArgs>(args?: SelectSubset<T, MarketSnapshotCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a MarketSnapshot.
     * @param {MarketSnapshotDeleteArgs} args - Arguments to delete one MarketSnapshot.
     * @example
     * // Delete one MarketSnapshot
     * const MarketSnapshot = await prisma.marketSnapshot.delete({
     *   where: {
     *     // ... filter to delete one MarketSnapshot
     *   }
     * })
     * 
     */
    delete<T extends MarketSnapshotDeleteArgs>(args: SelectSubset<T, MarketSnapshotDeleteArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one MarketSnapshot.
     * @param {MarketSnapshotUpdateArgs} args - Arguments to update one MarketSnapshot.
     * @example
     * // Update one MarketSnapshot
     * const marketSnapshot = await prisma.marketSnapshot.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends MarketSnapshotUpdateArgs>(args: SelectSubset<T, MarketSnapshotUpdateArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more MarketSnapshots.
     * @param {MarketSnapshotDeleteManyArgs} args - Arguments to filter MarketSnapshots to delete.
     * @example
     * // Delete a few MarketSnapshots
     * const { count } = await prisma.marketSnapshot.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends MarketSnapshotDeleteManyArgs>(args?: SelectSubset<T, MarketSnapshotDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more MarketSnapshots.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MarketSnapshotUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many MarketSnapshots
     * const marketSnapshot = await prisma.marketSnapshot.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends MarketSnapshotUpdateManyArgs>(args: SelectSubset<T, MarketSnapshotUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more MarketSnapshots and returns the data updated in the database.
     * @param {MarketSnapshotUpdateManyAndReturnArgs} args - Arguments to update many MarketSnapshots.
     * @example
     * // Update many MarketSnapshots
     * const marketSnapshot = await prisma.marketSnapshot.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more MarketSnapshots and only return the `id`
     * const marketSnapshotWithIdOnly = await prisma.marketSnapshot.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends MarketSnapshotUpdateManyAndReturnArgs>(args: SelectSubset<T, MarketSnapshotUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one MarketSnapshot.
     * @param {MarketSnapshotUpsertArgs} args - Arguments to update or create a MarketSnapshot.
     * @example
     * // Update or create a MarketSnapshot
     * const marketSnapshot = await prisma.marketSnapshot.upsert({
     *   create: {
     *     // ... data to create a MarketSnapshot
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the MarketSnapshot we want to update
     *   }
     * })
     */
    upsert<T extends MarketSnapshotUpsertArgs>(args: SelectSubset<T, MarketSnapshotUpsertArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of MarketSnapshots.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MarketSnapshotCountArgs} args - Arguments to filter MarketSnapshots to count.
     * @example
     * // Count the number of MarketSnapshots
     * const count = await prisma.marketSnapshot.count({
     *   where: {
     *     // ... the filter for the MarketSnapshots we want to count
     *   }
     * })
    **/
    count<T extends MarketSnapshotCountArgs>(
      args?: Subset<T, MarketSnapshotCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], MarketSnapshotCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a MarketSnapshot.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MarketSnapshotAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends MarketSnapshotAggregateArgs>(args: Subset<T, MarketSnapshotAggregateArgs>): Prisma.PrismaPromise<GetMarketSnapshotAggregateType<T>>

    /**
     * Group by MarketSnapshot.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {MarketSnapshotGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends MarketSnapshotGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: MarketSnapshotGroupByArgs['orderBy'] }
        : { orderBy?: MarketSnapshotGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, MarketSnapshotGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetMarketSnapshotGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the MarketSnapshot model
   */
  readonly fields: MarketSnapshotFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for MarketSnapshot.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__MarketSnapshotClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    bookLines<T extends MarketSnapshot$bookLinesArgs<ExtArgs> = {}>(args?: Subset<T, MarketSnapshot$bookLinesArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    game<T extends GameDefaultArgs<ExtArgs> = {}>(args?: Subset<T, GameDefaultArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the MarketSnapshot model
   */
  interface MarketSnapshotFieldRefs {
    readonly id: FieldRef<"MarketSnapshot", 'String'>
    readonly gameId: FieldRef<"MarketSnapshot", 'String'>
    readonly capturedAt: FieldRef<"MarketSnapshot", 'DateTime'>
    readonly openSpreadHome: FieldRef<"MarketSnapshot", 'Float'>
    readonly currentSpreadHome: FieldRef<"MarketSnapshot", 'Float'>
    readonly openTotal: FieldRef<"MarketSnapshot", 'Float'>
    readonly currentTotal: FieldRef<"MarketSnapshot", 'Float'>
    readonly bestSpreadHome: FieldRef<"MarketSnapshot", 'Float'>
    readonly bestSpreadBook: FieldRef<"MarketSnapshot", 'String'>
    readonly bestTotal: FieldRef<"MarketSnapshot", 'Float'>
    readonly bestTotalBook: FieldRef<"MarketSnapshot", 'String'>
    readonly spreadDispersion: FieldRef<"MarketSnapshot", 'Float'>
    readonly totalDispersion: FieldRef<"MarketSnapshot", 'Float'>
  }
    

  // Custom InputTypes
  /**
   * MarketSnapshot findUnique
   */
  export type MarketSnapshotFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    /**
     * Filter, which MarketSnapshot to fetch.
     */
    where: MarketSnapshotWhereUniqueInput
  }

  /**
   * MarketSnapshot findUniqueOrThrow
   */
  export type MarketSnapshotFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    /**
     * Filter, which MarketSnapshot to fetch.
     */
    where: MarketSnapshotWhereUniqueInput
  }

  /**
   * MarketSnapshot findFirst
   */
  export type MarketSnapshotFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    /**
     * Filter, which MarketSnapshot to fetch.
     */
    where?: MarketSnapshotWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of MarketSnapshots to fetch.
     */
    orderBy?: MarketSnapshotOrderByWithRelationInput | MarketSnapshotOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for MarketSnapshots.
     */
    cursor?: MarketSnapshotWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` MarketSnapshots from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` MarketSnapshots.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of MarketSnapshots.
     */
    distinct?: MarketSnapshotScalarFieldEnum | MarketSnapshotScalarFieldEnum[]
  }

  /**
   * MarketSnapshot findFirstOrThrow
   */
  export type MarketSnapshotFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    /**
     * Filter, which MarketSnapshot to fetch.
     */
    where?: MarketSnapshotWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of MarketSnapshots to fetch.
     */
    orderBy?: MarketSnapshotOrderByWithRelationInput | MarketSnapshotOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for MarketSnapshots.
     */
    cursor?: MarketSnapshotWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` MarketSnapshots from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` MarketSnapshots.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of MarketSnapshots.
     */
    distinct?: MarketSnapshotScalarFieldEnum | MarketSnapshotScalarFieldEnum[]
  }

  /**
   * MarketSnapshot findMany
   */
  export type MarketSnapshotFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    /**
     * Filter, which MarketSnapshots to fetch.
     */
    where?: MarketSnapshotWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of MarketSnapshots to fetch.
     */
    orderBy?: MarketSnapshotOrderByWithRelationInput | MarketSnapshotOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing MarketSnapshots.
     */
    cursor?: MarketSnapshotWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` MarketSnapshots from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` MarketSnapshots.
     */
    skip?: number
    distinct?: MarketSnapshotScalarFieldEnum | MarketSnapshotScalarFieldEnum[]
  }

  /**
   * MarketSnapshot create
   */
  export type MarketSnapshotCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    /**
     * The data needed to create a MarketSnapshot.
     */
    data: XOR<MarketSnapshotCreateInput, MarketSnapshotUncheckedCreateInput>
  }

  /**
   * MarketSnapshot createMany
   */
  export type MarketSnapshotCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many MarketSnapshots.
     */
    data: MarketSnapshotCreateManyInput | MarketSnapshotCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * MarketSnapshot createManyAndReturn
   */
  export type MarketSnapshotCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * The data used to create many MarketSnapshots.
     */
    data: MarketSnapshotCreateManyInput | MarketSnapshotCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * MarketSnapshot update
   */
  export type MarketSnapshotUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    /**
     * The data needed to update a MarketSnapshot.
     */
    data: XOR<MarketSnapshotUpdateInput, MarketSnapshotUncheckedUpdateInput>
    /**
     * Choose, which MarketSnapshot to update.
     */
    where: MarketSnapshotWhereUniqueInput
  }

  /**
   * MarketSnapshot updateMany
   */
  export type MarketSnapshotUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update MarketSnapshots.
     */
    data: XOR<MarketSnapshotUpdateManyMutationInput, MarketSnapshotUncheckedUpdateManyInput>
    /**
     * Filter which MarketSnapshots to update
     */
    where?: MarketSnapshotWhereInput
    /**
     * Limit how many MarketSnapshots to update.
     */
    limit?: number
  }

  /**
   * MarketSnapshot updateManyAndReturn
   */
  export type MarketSnapshotUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * The data used to update MarketSnapshots.
     */
    data: XOR<MarketSnapshotUpdateManyMutationInput, MarketSnapshotUncheckedUpdateManyInput>
    /**
     * Filter which MarketSnapshots to update
     */
    where?: MarketSnapshotWhereInput
    /**
     * Limit how many MarketSnapshots to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * MarketSnapshot upsert
   */
  export type MarketSnapshotUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    /**
     * The filter to search for the MarketSnapshot to update in case it exists.
     */
    where: MarketSnapshotWhereUniqueInput
    /**
     * In case the MarketSnapshot found by the `where` argument doesn't exist, create a new MarketSnapshot with this data.
     */
    create: XOR<MarketSnapshotCreateInput, MarketSnapshotUncheckedCreateInput>
    /**
     * In case the MarketSnapshot was found with the provided `where` argument, update it with this data.
     */
    update: XOR<MarketSnapshotUpdateInput, MarketSnapshotUncheckedUpdateInput>
  }

  /**
   * MarketSnapshot delete
   */
  export type MarketSnapshotDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
    /**
     * Filter which MarketSnapshot to delete.
     */
    where: MarketSnapshotWhereUniqueInput
  }

  /**
   * MarketSnapshot deleteMany
   */
  export type MarketSnapshotDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which MarketSnapshots to delete
     */
    where?: MarketSnapshotWhereInput
    /**
     * Limit how many MarketSnapshots to delete.
     */
    limit?: number
  }

  /**
   * MarketSnapshot.bookLines
   */
  export type MarketSnapshot$bookLinesArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    where?: BookLineWhereInput
    orderBy?: BookLineOrderByWithRelationInput | BookLineOrderByWithRelationInput[]
    cursor?: BookLineWhereUniqueInput
    take?: number
    skip?: number
    distinct?: BookLineScalarFieldEnum | BookLineScalarFieldEnum[]
  }

  /**
   * MarketSnapshot without action
   */
  export type MarketSnapshotDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the MarketSnapshot
     */
    select?: MarketSnapshotSelect<ExtArgs> | null
    /**
     * Omit specific fields from the MarketSnapshot
     */
    omit?: MarketSnapshotOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: MarketSnapshotInclude<ExtArgs> | null
  }


  /**
   * Model BookLine
   */

  export type AggregateBookLine = {
    _count: BookLineCountAggregateOutputType | null
    _avg: BookLineAvgAggregateOutputType | null
    _sum: BookLineSumAggregateOutputType | null
    _min: BookLineMinAggregateOutputType | null
    _max: BookLineMaxAggregateOutputType | null
  }

  export type BookLineAvgAggregateOutputType = {
    spreadHome: number | null
    spreadAway: number | null
    total: number | null
  }

  export type BookLineSumAggregateOutputType = {
    spreadHome: number | null
    spreadAway: number | null
    total: number | null
  }

  export type BookLineMinAggregateOutputType = {
    id: string | null
    marketId: string | null
    book: string | null
    capturedAt: Date | null
    spreadHome: number | null
    spreadAway: number | null
    total: number | null
  }

  export type BookLineMaxAggregateOutputType = {
    id: string | null
    marketId: string | null
    book: string | null
    capturedAt: Date | null
    spreadHome: number | null
    spreadAway: number | null
    total: number | null
  }

  export type BookLineCountAggregateOutputType = {
    id: number
    marketId: number
    book: number
    capturedAt: number
    spreadHome: number
    spreadAway: number
    total: number
    _all: number
  }


  export type BookLineAvgAggregateInputType = {
    spreadHome?: true
    spreadAway?: true
    total?: true
  }

  export type BookLineSumAggregateInputType = {
    spreadHome?: true
    spreadAway?: true
    total?: true
  }

  export type BookLineMinAggregateInputType = {
    id?: true
    marketId?: true
    book?: true
    capturedAt?: true
    spreadHome?: true
    spreadAway?: true
    total?: true
  }

  export type BookLineMaxAggregateInputType = {
    id?: true
    marketId?: true
    book?: true
    capturedAt?: true
    spreadHome?: true
    spreadAway?: true
    total?: true
  }

  export type BookLineCountAggregateInputType = {
    id?: true
    marketId?: true
    book?: true
    capturedAt?: true
    spreadHome?: true
    spreadAway?: true
    total?: true
    _all?: true
  }

  export type BookLineAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which BookLine to aggregate.
     */
    where?: BookLineWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of BookLines to fetch.
     */
    orderBy?: BookLineOrderByWithRelationInput | BookLineOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: BookLineWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` BookLines from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` BookLines.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned BookLines
    **/
    _count?: true | BookLineCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to average
    **/
    _avg?: BookLineAvgAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to sum
    **/
    _sum?: BookLineSumAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: BookLineMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: BookLineMaxAggregateInputType
  }

  export type GetBookLineAggregateType<T extends BookLineAggregateArgs> = {
        [P in keyof T & keyof AggregateBookLine]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateBookLine[P]>
      : GetScalarType<T[P], AggregateBookLine[P]>
  }




  export type BookLineGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: BookLineWhereInput
    orderBy?: BookLineOrderByWithAggregationInput | BookLineOrderByWithAggregationInput[]
    by: BookLineScalarFieldEnum[] | BookLineScalarFieldEnum
    having?: BookLineScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: BookLineCountAggregateInputType | true
    _avg?: BookLineAvgAggregateInputType
    _sum?: BookLineSumAggregateInputType
    _min?: BookLineMinAggregateInputType
    _max?: BookLineMaxAggregateInputType
  }

  export type BookLineGroupByOutputType = {
    id: string
    marketId: string
    book: string
    capturedAt: Date
    spreadHome: number | null
    spreadAway: number | null
    total: number | null
    _count: BookLineCountAggregateOutputType | null
    _avg: BookLineAvgAggregateOutputType | null
    _sum: BookLineSumAggregateOutputType | null
    _min: BookLineMinAggregateOutputType | null
    _max: BookLineMaxAggregateOutputType | null
  }

  type GetBookLineGroupByPayload<T extends BookLineGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<BookLineGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof BookLineGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], BookLineGroupByOutputType[P]>
            : GetScalarType<T[P], BookLineGroupByOutputType[P]>
        }
      >
    >


  export type BookLineSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    marketId?: boolean
    book?: boolean
    capturedAt?: boolean
    spreadHome?: boolean
    spreadAway?: boolean
    total?: boolean
    market?: boolean | MarketSnapshotDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["bookLine"]>

  export type BookLineSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    marketId?: boolean
    book?: boolean
    capturedAt?: boolean
    spreadHome?: boolean
    spreadAway?: boolean
    total?: boolean
    market?: boolean | MarketSnapshotDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["bookLine"]>

  export type BookLineSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    marketId?: boolean
    book?: boolean
    capturedAt?: boolean
    spreadHome?: boolean
    spreadAway?: boolean
    total?: boolean
    market?: boolean | MarketSnapshotDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["bookLine"]>

  export type BookLineSelectScalar = {
    id?: boolean
    marketId?: boolean
    book?: boolean
    capturedAt?: boolean
    spreadHome?: boolean
    spreadAway?: boolean
    total?: boolean
  }

  export type BookLineOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "marketId" | "book" | "capturedAt" | "spreadHome" | "spreadAway" | "total", ExtArgs["result"]["bookLine"]>
  export type BookLineInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    market?: boolean | MarketSnapshotDefaultArgs<ExtArgs>
  }
  export type BookLineIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    market?: boolean | MarketSnapshotDefaultArgs<ExtArgs>
  }
  export type BookLineIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    market?: boolean | MarketSnapshotDefaultArgs<ExtArgs>
  }

  export type $BookLinePayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "BookLine"
    objects: {
      market: Prisma.$MarketSnapshotPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      marketId: string
      book: string
      capturedAt: Date
      spreadHome: number | null
      spreadAway: number | null
      total: number | null
    }, ExtArgs["result"]["bookLine"]>
    composites: {}
  }

  type BookLineGetPayload<S extends boolean | null | undefined | BookLineDefaultArgs> = $Result.GetResult<Prisma.$BookLinePayload, S>

  type BookLineCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<BookLineFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: BookLineCountAggregateInputType | true
    }

  export interface BookLineDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['BookLine'], meta: { name: 'BookLine' } }
    /**
     * Find zero or one BookLine that matches the filter.
     * @param {BookLineFindUniqueArgs} args - Arguments to find a BookLine
     * @example
     * // Get one BookLine
     * const bookLine = await prisma.bookLine.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends BookLineFindUniqueArgs>(args: SelectSubset<T, BookLineFindUniqueArgs<ExtArgs>>): Prisma__BookLineClient<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one BookLine that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {BookLineFindUniqueOrThrowArgs} args - Arguments to find a BookLine
     * @example
     * // Get one BookLine
     * const bookLine = await prisma.bookLine.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends BookLineFindUniqueOrThrowArgs>(args: SelectSubset<T, BookLineFindUniqueOrThrowArgs<ExtArgs>>): Prisma__BookLineClient<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first BookLine that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {BookLineFindFirstArgs} args - Arguments to find a BookLine
     * @example
     * // Get one BookLine
     * const bookLine = await prisma.bookLine.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends BookLineFindFirstArgs>(args?: SelectSubset<T, BookLineFindFirstArgs<ExtArgs>>): Prisma__BookLineClient<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first BookLine that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {BookLineFindFirstOrThrowArgs} args - Arguments to find a BookLine
     * @example
     * // Get one BookLine
     * const bookLine = await prisma.bookLine.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends BookLineFindFirstOrThrowArgs>(args?: SelectSubset<T, BookLineFindFirstOrThrowArgs<ExtArgs>>): Prisma__BookLineClient<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more BookLines that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {BookLineFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all BookLines
     * const bookLines = await prisma.bookLine.findMany()
     * 
     * // Get first 10 BookLines
     * const bookLines = await prisma.bookLine.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const bookLineWithIdOnly = await prisma.bookLine.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends BookLineFindManyArgs>(args?: SelectSubset<T, BookLineFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a BookLine.
     * @param {BookLineCreateArgs} args - Arguments to create a BookLine.
     * @example
     * // Create one BookLine
     * const BookLine = await prisma.bookLine.create({
     *   data: {
     *     // ... data to create a BookLine
     *   }
     * })
     * 
     */
    create<T extends BookLineCreateArgs>(args: SelectSubset<T, BookLineCreateArgs<ExtArgs>>): Prisma__BookLineClient<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many BookLines.
     * @param {BookLineCreateManyArgs} args - Arguments to create many BookLines.
     * @example
     * // Create many BookLines
     * const bookLine = await prisma.bookLine.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends BookLineCreateManyArgs>(args?: SelectSubset<T, BookLineCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many BookLines and returns the data saved in the database.
     * @param {BookLineCreateManyAndReturnArgs} args - Arguments to create many BookLines.
     * @example
     * // Create many BookLines
     * const bookLine = await prisma.bookLine.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many BookLines and only return the `id`
     * const bookLineWithIdOnly = await prisma.bookLine.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends BookLineCreateManyAndReturnArgs>(args?: SelectSubset<T, BookLineCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a BookLine.
     * @param {BookLineDeleteArgs} args - Arguments to delete one BookLine.
     * @example
     * // Delete one BookLine
     * const BookLine = await prisma.bookLine.delete({
     *   where: {
     *     // ... filter to delete one BookLine
     *   }
     * })
     * 
     */
    delete<T extends BookLineDeleteArgs>(args: SelectSubset<T, BookLineDeleteArgs<ExtArgs>>): Prisma__BookLineClient<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one BookLine.
     * @param {BookLineUpdateArgs} args - Arguments to update one BookLine.
     * @example
     * // Update one BookLine
     * const bookLine = await prisma.bookLine.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends BookLineUpdateArgs>(args: SelectSubset<T, BookLineUpdateArgs<ExtArgs>>): Prisma__BookLineClient<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more BookLines.
     * @param {BookLineDeleteManyArgs} args - Arguments to filter BookLines to delete.
     * @example
     * // Delete a few BookLines
     * const { count } = await prisma.bookLine.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends BookLineDeleteManyArgs>(args?: SelectSubset<T, BookLineDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more BookLines.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {BookLineUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many BookLines
     * const bookLine = await prisma.bookLine.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends BookLineUpdateManyArgs>(args: SelectSubset<T, BookLineUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more BookLines and returns the data updated in the database.
     * @param {BookLineUpdateManyAndReturnArgs} args - Arguments to update many BookLines.
     * @example
     * // Update many BookLines
     * const bookLine = await prisma.bookLine.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more BookLines and only return the `id`
     * const bookLineWithIdOnly = await prisma.bookLine.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends BookLineUpdateManyAndReturnArgs>(args: SelectSubset<T, BookLineUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one BookLine.
     * @param {BookLineUpsertArgs} args - Arguments to update or create a BookLine.
     * @example
     * // Update or create a BookLine
     * const bookLine = await prisma.bookLine.upsert({
     *   create: {
     *     // ... data to create a BookLine
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the BookLine we want to update
     *   }
     * })
     */
    upsert<T extends BookLineUpsertArgs>(args: SelectSubset<T, BookLineUpsertArgs<ExtArgs>>): Prisma__BookLineClient<$Result.GetResult<Prisma.$BookLinePayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of BookLines.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {BookLineCountArgs} args - Arguments to filter BookLines to count.
     * @example
     * // Count the number of BookLines
     * const count = await prisma.bookLine.count({
     *   where: {
     *     // ... the filter for the BookLines we want to count
     *   }
     * })
    **/
    count<T extends BookLineCountArgs>(
      args?: Subset<T, BookLineCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], BookLineCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a BookLine.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {BookLineAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends BookLineAggregateArgs>(args: Subset<T, BookLineAggregateArgs>): Prisma.PrismaPromise<GetBookLineAggregateType<T>>

    /**
     * Group by BookLine.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {BookLineGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends BookLineGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: BookLineGroupByArgs['orderBy'] }
        : { orderBy?: BookLineGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, BookLineGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetBookLineGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the BookLine model
   */
  readonly fields: BookLineFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for BookLine.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__BookLineClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    market<T extends MarketSnapshotDefaultArgs<ExtArgs> = {}>(args?: Subset<T, MarketSnapshotDefaultArgs<ExtArgs>>): Prisma__MarketSnapshotClient<$Result.GetResult<Prisma.$MarketSnapshotPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the BookLine model
   */
  interface BookLineFieldRefs {
    readonly id: FieldRef<"BookLine", 'String'>
    readonly marketId: FieldRef<"BookLine", 'String'>
    readonly book: FieldRef<"BookLine", 'String'>
    readonly capturedAt: FieldRef<"BookLine", 'DateTime'>
    readonly spreadHome: FieldRef<"BookLine", 'Float'>
    readonly spreadAway: FieldRef<"BookLine", 'Float'>
    readonly total: FieldRef<"BookLine", 'Float'>
  }
    

  // Custom InputTypes
  /**
   * BookLine findUnique
   */
  export type BookLineFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    /**
     * Filter, which BookLine to fetch.
     */
    where: BookLineWhereUniqueInput
  }

  /**
   * BookLine findUniqueOrThrow
   */
  export type BookLineFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    /**
     * Filter, which BookLine to fetch.
     */
    where: BookLineWhereUniqueInput
  }

  /**
   * BookLine findFirst
   */
  export type BookLineFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    /**
     * Filter, which BookLine to fetch.
     */
    where?: BookLineWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of BookLines to fetch.
     */
    orderBy?: BookLineOrderByWithRelationInput | BookLineOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for BookLines.
     */
    cursor?: BookLineWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` BookLines from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` BookLines.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of BookLines.
     */
    distinct?: BookLineScalarFieldEnum | BookLineScalarFieldEnum[]
  }

  /**
   * BookLine findFirstOrThrow
   */
  export type BookLineFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    /**
     * Filter, which BookLine to fetch.
     */
    where?: BookLineWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of BookLines to fetch.
     */
    orderBy?: BookLineOrderByWithRelationInput | BookLineOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for BookLines.
     */
    cursor?: BookLineWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` BookLines from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` BookLines.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of BookLines.
     */
    distinct?: BookLineScalarFieldEnum | BookLineScalarFieldEnum[]
  }

  /**
   * BookLine findMany
   */
  export type BookLineFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    /**
     * Filter, which BookLines to fetch.
     */
    where?: BookLineWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of BookLines to fetch.
     */
    orderBy?: BookLineOrderByWithRelationInput | BookLineOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing BookLines.
     */
    cursor?: BookLineWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` BookLines from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` BookLines.
     */
    skip?: number
    distinct?: BookLineScalarFieldEnum | BookLineScalarFieldEnum[]
  }

  /**
   * BookLine create
   */
  export type BookLineCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    /**
     * The data needed to create a BookLine.
     */
    data: XOR<BookLineCreateInput, BookLineUncheckedCreateInput>
  }

  /**
   * BookLine createMany
   */
  export type BookLineCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many BookLines.
     */
    data: BookLineCreateManyInput | BookLineCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * BookLine createManyAndReturn
   */
  export type BookLineCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * The data used to create many BookLines.
     */
    data: BookLineCreateManyInput | BookLineCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * BookLine update
   */
  export type BookLineUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    /**
     * The data needed to update a BookLine.
     */
    data: XOR<BookLineUpdateInput, BookLineUncheckedUpdateInput>
    /**
     * Choose, which BookLine to update.
     */
    where: BookLineWhereUniqueInput
  }

  /**
   * BookLine updateMany
   */
  export type BookLineUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update BookLines.
     */
    data: XOR<BookLineUpdateManyMutationInput, BookLineUncheckedUpdateManyInput>
    /**
     * Filter which BookLines to update
     */
    where?: BookLineWhereInput
    /**
     * Limit how many BookLines to update.
     */
    limit?: number
  }

  /**
   * BookLine updateManyAndReturn
   */
  export type BookLineUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * The data used to update BookLines.
     */
    data: XOR<BookLineUpdateManyMutationInput, BookLineUncheckedUpdateManyInput>
    /**
     * Filter which BookLines to update
     */
    where?: BookLineWhereInput
    /**
     * Limit how many BookLines to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * BookLine upsert
   */
  export type BookLineUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    /**
     * The filter to search for the BookLine to update in case it exists.
     */
    where: BookLineWhereUniqueInput
    /**
     * In case the BookLine found by the `where` argument doesn't exist, create a new BookLine with this data.
     */
    create: XOR<BookLineCreateInput, BookLineUncheckedCreateInput>
    /**
     * In case the BookLine was found with the provided `where` argument, update it with this data.
     */
    update: XOR<BookLineUpdateInput, BookLineUncheckedUpdateInput>
  }

  /**
   * BookLine delete
   */
  export type BookLineDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
    /**
     * Filter which BookLine to delete.
     */
    where: BookLineWhereUniqueInput
  }

  /**
   * BookLine deleteMany
   */
  export type BookLineDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which BookLines to delete
     */
    where?: BookLineWhereInput
    /**
     * Limit how many BookLines to delete.
     */
    limit?: number
  }

  /**
   * BookLine without action
   */
  export type BookLineDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the BookLine
     */
    select?: BookLineSelect<ExtArgs> | null
    /**
     * Omit specific fields from the BookLine
     */
    omit?: BookLineOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: BookLineInclude<ExtArgs> | null
  }


  /**
   * Model ModelProjection
   */

  export type AggregateModelProjection = {
    _count: ModelProjectionCountAggregateOutputType | null
    _avg: ModelProjectionAvgAggregateOutputType | null
    _sum: ModelProjectionSumAggregateOutputType | null
    _min: ModelProjectionMinAggregateOutputType | null
    _max: ModelProjectionMaxAggregateOutputType | null
  }

  export type ModelProjectionAvgAggregateOutputType = {
    projSpreadHome: number | null
    projTotal: number | null
  }

  export type ModelProjectionSumAggregateOutputType = {
    projSpreadHome: number | null
    projTotal: number | null
  }

  export type ModelProjectionMinAggregateOutputType = {
    id: string | null
    gameId: string | null
    version: string | null
    computedAt: Date | null
    projSpreadHome: number | null
    projTotal: number | null
  }

  export type ModelProjectionMaxAggregateOutputType = {
    id: string | null
    gameId: string | null
    version: string | null
    computedAt: Date | null
    projSpreadHome: number | null
    projTotal: number | null
  }

  export type ModelProjectionCountAggregateOutputType = {
    id: number
    gameId: number
    version: number
    computedAt: number
    projSpreadHome: number
    projTotal: number
    _all: number
  }


  export type ModelProjectionAvgAggregateInputType = {
    projSpreadHome?: true
    projTotal?: true
  }

  export type ModelProjectionSumAggregateInputType = {
    projSpreadHome?: true
    projTotal?: true
  }

  export type ModelProjectionMinAggregateInputType = {
    id?: true
    gameId?: true
    version?: true
    computedAt?: true
    projSpreadHome?: true
    projTotal?: true
  }

  export type ModelProjectionMaxAggregateInputType = {
    id?: true
    gameId?: true
    version?: true
    computedAt?: true
    projSpreadHome?: true
    projTotal?: true
  }

  export type ModelProjectionCountAggregateInputType = {
    id?: true
    gameId?: true
    version?: true
    computedAt?: true
    projSpreadHome?: true
    projTotal?: true
    _all?: true
  }

  export type ModelProjectionAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which ModelProjection to aggregate.
     */
    where?: ModelProjectionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of ModelProjections to fetch.
     */
    orderBy?: ModelProjectionOrderByWithRelationInput | ModelProjectionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: ModelProjectionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` ModelProjections from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` ModelProjections.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned ModelProjections
    **/
    _count?: true | ModelProjectionCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to average
    **/
    _avg?: ModelProjectionAvgAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to sum
    **/
    _sum?: ModelProjectionSumAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: ModelProjectionMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: ModelProjectionMaxAggregateInputType
  }

  export type GetModelProjectionAggregateType<T extends ModelProjectionAggregateArgs> = {
        [P in keyof T & keyof AggregateModelProjection]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateModelProjection[P]>
      : GetScalarType<T[P], AggregateModelProjection[P]>
  }




  export type ModelProjectionGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: ModelProjectionWhereInput
    orderBy?: ModelProjectionOrderByWithAggregationInput | ModelProjectionOrderByWithAggregationInput[]
    by: ModelProjectionScalarFieldEnum[] | ModelProjectionScalarFieldEnum
    having?: ModelProjectionScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: ModelProjectionCountAggregateInputType | true
    _avg?: ModelProjectionAvgAggregateInputType
    _sum?: ModelProjectionSumAggregateInputType
    _min?: ModelProjectionMinAggregateInputType
    _max?: ModelProjectionMaxAggregateInputType
  }

  export type ModelProjectionGroupByOutputType = {
    id: string
    gameId: string
    version: string
    computedAt: Date
    projSpreadHome: number
    projTotal: number
    _count: ModelProjectionCountAggregateOutputType | null
    _avg: ModelProjectionAvgAggregateOutputType | null
    _sum: ModelProjectionSumAggregateOutputType | null
    _min: ModelProjectionMinAggregateOutputType | null
    _max: ModelProjectionMaxAggregateOutputType | null
  }

  type GetModelProjectionGroupByPayload<T extends ModelProjectionGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<ModelProjectionGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof ModelProjectionGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], ModelProjectionGroupByOutputType[P]>
            : GetScalarType<T[P], ModelProjectionGroupByOutputType[P]>
        }
      >
    >


  export type ModelProjectionSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    gameId?: boolean
    version?: boolean
    computedAt?: boolean
    projSpreadHome?: boolean
    projTotal?: boolean
    game?: boolean | GameDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["modelProjection"]>

  export type ModelProjectionSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    gameId?: boolean
    version?: boolean
    computedAt?: boolean
    projSpreadHome?: boolean
    projTotal?: boolean
    game?: boolean | GameDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["modelProjection"]>

  export type ModelProjectionSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    gameId?: boolean
    version?: boolean
    computedAt?: boolean
    projSpreadHome?: boolean
    projTotal?: boolean
    game?: boolean | GameDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["modelProjection"]>

  export type ModelProjectionSelectScalar = {
    id?: boolean
    gameId?: boolean
    version?: boolean
    computedAt?: boolean
    projSpreadHome?: boolean
    projTotal?: boolean
  }

  export type ModelProjectionOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "gameId" | "version" | "computedAt" | "projSpreadHome" | "projTotal", ExtArgs["result"]["modelProjection"]>
  export type ModelProjectionInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    game?: boolean | GameDefaultArgs<ExtArgs>
  }
  export type ModelProjectionIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    game?: boolean | GameDefaultArgs<ExtArgs>
  }
  export type ModelProjectionIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    game?: boolean | GameDefaultArgs<ExtArgs>
  }

  export type $ModelProjectionPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "ModelProjection"
    objects: {
      game: Prisma.$GamePayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      gameId: string
      version: string
      computedAt: Date
      projSpreadHome: number
      projTotal: number
    }, ExtArgs["result"]["modelProjection"]>
    composites: {}
  }

  type ModelProjectionGetPayload<S extends boolean | null | undefined | ModelProjectionDefaultArgs> = $Result.GetResult<Prisma.$ModelProjectionPayload, S>

  type ModelProjectionCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<ModelProjectionFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: ModelProjectionCountAggregateInputType | true
    }

  export interface ModelProjectionDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['ModelProjection'], meta: { name: 'ModelProjection' } }
    /**
     * Find zero or one ModelProjection that matches the filter.
     * @param {ModelProjectionFindUniqueArgs} args - Arguments to find a ModelProjection
     * @example
     * // Get one ModelProjection
     * const modelProjection = await prisma.modelProjection.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends ModelProjectionFindUniqueArgs>(args: SelectSubset<T, ModelProjectionFindUniqueArgs<ExtArgs>>): Prisma__ModelProjectionClient<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one ModelProjection that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {ModelProjectionFindUniqueOrThrowArgs} args - Arguments to find a ModelProjection
     * @example
     * // Get one ModelProjection
     * const modelProjection = await prisma.modelProjection.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends ModelProjectionFindUniqueOrThrowArgs>(args: SelectSubset<T, ModelProjectionFindUniqueOrThrowArgs<ExtArgs>>): Prisma__ModelProjectionClient<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first ModelProjection that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ModelProjectionFindFirstArgs} args - Arguments to find a ModelProjection
     * @example
     * // Get one ModelProjection
     * const modelProjection = await prisma.modelProjection.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends ModelProjectionFindFirstArgs>(args?: SelectSubset<T, ModelProjectionFindFirstArgs<ExtArgs>>): Prisma__ModelProjectionClient<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first ModelProjection that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ModelProjectionFindFirstOrThrowArgs} args - Arguments to find a ModelProjection
     * @example
     * // Get one ModelProjection
     * const modelProjection = await prisma.modelProjection.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends ModelProjectionFindFirstOrThrowArgs>(args?: SelectSubset<T, ModelProjectionFindFirstOrThrowArgs<ExtArgs>>): Prisma__ModelProjectionClient<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more ModelProjections that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ModelProjectionFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all ModelProjections
     * const modelProjections = await prisma.modelProjection.findMany()
     * 
     * // Get first 10 ModelProjections
     * const modelProjections = await prisma.modelProjection.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const modelProjectionWithIdOnly = await prisma.modelProjection.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends ModelProjectionFindManyArgs>(args?: SelectSubset<T, ModelProjectionFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a ModelProjection.
     * @param {ModelProjectionCreateArgs} args - Arguments to create a ModelProjection.
     * @example
     * // Create one ModelProjection
     * const ModelProjection = await prisma.modelProjection.create({
     *   data: {
     *     // ... data to create a ModelProjection
     *   }
     * })
     * 
     */
    create<T extends ModelProjectionCreateArgs>(args: SelectSubset<T, ModelProjectionCreateArgs<ExtArgs>>): Prisma__ModelProjectionClient<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many ModelProjections.
     * @param {ModelProjectionCreateManyArgs} args - Arguments to create many ModelProjections.
     * @example
     * // Create many ModelProjections
     * const modelProjection = await prisma.modelProjection.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends ModelProjectionCreateManyArgs>(args?: SelectSubset<T, ModelProjectionCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many ModelProjections and returns the data saved in the database.
     * @param {ModelProjectionCreateManyAndReturnArgs} args - Arguments to create many ModelProjections.
     * @example
     * // Create many ModelProjections
     * const modelProjection = await prisma.modelProjection.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many ModelProjections and only return the `id`
     * const modelProjectionWithIdOnly = await prisma.modelProjection.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends ModelProjectionCreateManyAndReturnArgs>(args?: SelectSubset<T, ModelProjectionCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a ModelProjection.
     * @param {ModelProjectionDeleteArgs} args - Arguments to delete one ModelProjection.
     * @example
     * // Delete one ModelProjection
     * const ModelProjection = await prisma.modelProjection.delete({
     *   where: {
     *     // ... filter to delete one ModelProjection
     *   }
     * })
     * 
     */
    delete<T extends ModelProjectionDeleteArgs>(args: SelectSubset<T, ModelProjectionDeleteArgs<ExtArgs>>): Prisma__ModelProjectionClient<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one ModelProjection.
     * @param {ModelProjectionUpdateArgs} args - Arguments to update one ModelProjection.
     * @example
     * // Update one ModelProjection
     * const modelProjection = await prisma.modelProjection.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends ModelProjectionUpdateArgs>(args: SelectSubset<T, ModelProjectionUpdateArgs<ExtArgs>>): Prisma__ModelProjectionClient<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more ModelProjections.
     * @param {ModelProjectionDeleteManyArgs} args - Arguments to filter ModelProjections to delete.
     * @example
     * // Delete a few ModelProjections
     * const { count } = await prisma.modelProjection.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends ModelProjectionDeleteManyArgs>(args?: SelectSubset<T, ModelProjectionDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more ModelProjections.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ModelProjectionUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many ModelProjections
     * const modelProjection = await prisma.modelProjection.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends ModelProjectionUpdateManyArgs>(args: SelectSubset<T, ModelProjectionUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more ModelProjections and returns the data updated in the database.
     * @param {ModelProjectionUpdateManyAndReturnArgs} args - Arguments to update many ModelProjections.
     * @example
     * // Update many ModelProjections
     * const modelProjection = await prisma.modelProjection.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more ModelProjections and only return the `id`
     * const modelProjectionWithIdOnly = await prisma.modelProjection.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends ModelProjectionUpdateManyAndReturnArgs>(args: SelectSubset<T, ModelProjectionUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one ModelProjection.
     * @param {ModelProjectionUpsertArgs} args - Arguments to update or create a ModelProjection.
     * @example
     * // Update or create a ModelProjection
     * const modelProjection = await prisma.modelProjection.upsert({
     *   create: {
     *     // ... data to create a ModelProjection
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the ModelProjection we want to update
     *   }
     * })
     */
    upsert<T extends ModelProjectionUpsertArgs>(args: SelectSubset<T, ModelProjectionUpsertArgs<ExtArgs>>): Prisma__ModelProjectionClient<$Result.GetResult<Prisma.$ModelProjectionPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of ModelProjections.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ModelProjectionCountArgs} args - Arguments to filter ModelProjections to count.
     * @example
     * // Count the number of ModelProjections
     * const count = await prisma.modelProjection.count({
     *   where: {
     *     // ... the filter for the ModelProjections we want to count
     *   }
     * })
    **/
    count<T extends ModelProjectionCountArgs>(
      args?: Subset<T, ModelProjectionCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], ModelProjectionCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a ModelProjection.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ModelProjectionAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends ModelProjectionAggregateArgs>(args: Subset<T, ModelProjectionAggregateArgs>): Prisma.PrismaPromise<GetModelProjectionAggregateType<T>>

    /**
     * Group by ModelProjection.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ModelProjectionGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends ModelProjectionGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: ModelProjectionGroupByArgs['orderBy'] }
        : { orderBy?: ModelProjectionGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, ModelProjectionGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetModelProjectionGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the ModelProjection model
   */
  readonly fields: ModelProjectionFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for ModelProjection.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__ModelProjectionClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    game<T extends GameDefaultArgs<ExtArgs> = {}>(args?: Subset<T, GameDefaultArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the ModelProjection model
   */
  interface ModelProjectionFieldRefs {
    readonly id: FieldRef<"ModelProjection", 'String'>
    readonly gameId: FieldRef<"ModelProjection", 'String'>
    readonly version: FieldRef<"ModelProjection", 'String'>
    readonly computedAt: FieldRef<"ModelProjection", 'DateTime'>
    readonly projSpreadHome: FieldRef<"ModelProjection", 'Float'>
    readonly projTotal: FieldRef<"ModelProjection", 'Float'>
  }
    

  // Custom InputTypes
  /**
   * ModelProjection findUnique
   */
  export type ModelProjectionFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    /**
     * Filter, which ModelProjection to fetch.
     */
    where: ModelProjectionWhereUniqueInput
  }

  /**
   * ModelProjection findUniqueOrThrow
   */
  export type ModelProjectionFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    /**
     * Filter, which ModelProjection to fetch.
     */
    where: ModelProjectionWhereUniqueInput
  }

  /**
   * ModelProjection findFirst
   */
  export type ModelProjectionFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    /**
     * Filter, which ModelProjection to fetch.
     */
    where?: ModelProjectionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of ModelProjections to fetch.
     */
    orderBy?: ModelProjectionOrderByWithRelationInput | ModelProjectionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for ModelProjections.
     */
    cursor?: ModelProjectionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` ModelProjections from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` ModelProjections.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of ModelProjections.
     */
    distinct?: ModelProjectionScalarFieldEnum | ModelProjectionScalarFieldEnum[]
  }

  /**
   * ModelProjection findFirstOrThrow
   */
  export type ModelProjectionFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    /**
     * Filter, which ModelProjection to fetch.
     */
    where?: ModelProjectionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of ModelProjections to fetch.
     */
    orderBy?: ModelProjectionOrderByWithRelationInput | ModelProjectionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for ModelProjections.
     */
    cursor?: ModelProjectionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` ModelProjections from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` ModelProjections.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of ModelProjections.
     */
    distinct?: ModelProjectionScalarFieldEnum | ModelProjectionScalarFieldEnum[]
  }

  /**
   * ModelProjection findMany
   */
  export type ModelProjectionFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    /**
     * Filter, which ModelProjections to fetch.
     */
    where?: ModelProjectionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of ModelProjections to fetch.
     */
    orderBy?: ModelProjectionOrderByWithRelationInput | ModelProjectionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing ModelProjections.
     */
    cursor?: ModelProjectionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` ModelProjections from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` ModelProjections.
     */
    skip?: number
    distinct?: ModelProjectionScalarFieldEnum | ModelProjectionScalarFieldEnum[]
  }

  /**
   * ModelProjection create
   */
  export type ModelProjectionCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    /**
     * The data needed to create a ModelProjection.
     */
    data: XOR<ModelProjectionCreateInput, ModelProjectionUncheckedCreateInput>
  }

  /**
   * ModelProjection createMany
   */
  export type ModelProjectionCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many ModelProjections.
     */
    data: ModelProjectionCreateManyInput | ModelProjectionCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * ModelProjection createManyAndReturn
   */
  export type ModelProjectionCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * The data used to create many ModelProjections.
     */
    data: ModelProjectionCreateManyInput | ModelProjectionCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * ModelProjection update
   */
  export type ModelProjectionUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    /**
     * The data needed to update a ModelProjection.
     */
    data: XOR<ModelProjectionUpdateInput, ModelProjectionUncheckedUpdateInput>
    /**
     * Choose, which ModelProjection to update.
     */
    where: ModelProjectionWhereUniqueInput
  }

  /**
   * ModelProjection updateMany
   */
  export type ModelProjectionUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update ModelProjections.
     */
    data: XOR<ModelProjectionUpdateManyMutationInput, ModelProjectionUncheckedUpdateManyInput>
    /**
     * Filter which ModelProjections to update
     */
    where?: ModelProjectionWhereInput
    /**
     * Limit how many ModelProjections to update.
     */
    limit?: number
  }

  /**
   * ModelProjection updateManyAndReturn
   */
  export type ModelProjectionUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * The data used to update ModelProjections.
     */
    data: XOR<ModelProjectionUpdateManyMutationInput, ModelProjectionUncheckedUpdateManyInput>
    /**
     * Filter which ModelProjections to update
     */
    where?: ModelProjectionWhereInput
    /**
     * Limit how many ModelProjections to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * ModelProjection upsert
   */
  export type ModelProjectionUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    /**
     * The filter to search for the ModelProjection to update in case it exists.
     */
    where: ModelProjectionWhereUniqueInput
    /**
     * In case the ModelProjection found by the `where` argument doesn't exist, create a new ModelProjection with this data.
     */
    create: XOR<ModelProjectionCreateInput, ModelProjectionUncheckedCreateInput>
    /**
     * In case the ModelProjection was found with the provided `where` argument, update it with this data.
     */
    update: XOR<ModelProjectionUpdateInput, ModelProjectionUncheckedUpdateInput>
  }

  /**
   * ModelProjection delete
   */
  export type ModelProjectionDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
    /**
     * Filter which ModelProjection to delete.
     */
    where: ModelProjectionWhereUniqueInput
  }

  /**
   * ModelProjection deleteMany
   */
  export type ModelProjectionDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which ModelProjections to delete
     */
    where?: ModelProjectionWhereInput
    /**
     * Limit how many ModelProjections to delete.
     */
    limit?: number
  }

  /**
   * ModelProjection without action
   */
  export type ModelProjectionDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ModelProjection
     */
    select?: ModelProjectionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the ModelProjection
     */
    omit?: ModelProjectionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ModelProjectionInclude<ExtArgs> | null
  }


  /**
   * Model Writeup
   */

  export type AggregateWriteup = {
    _count: WriteupCountAggregateOutputType | null
    _min: WriteupMinAggregateOutputType | null
    _max: WriteupMaxAggregateOutputType | null
  }

  export type WriteupMinAggregateOutputType = {
    id: string | null
    gameId: string | null
    createdAt: Date | null
    updatedAt: Date | null
    formatKey: string | null
    body: string | null
    disclosedAi: boolean | null
    editorStatus: $Enums.EditorStatus | null
  }

  export type WriteupMaxAggregateOutputType = {
    id: string | null
    gameId: string | null
    createdAt: Date | null
    updatedAt: Date | null
    formatKey: string | null
    body: string | null
    disclosedAi: boolean | null
    editorStatus: $Enums.EditorStatus | null
  }

  export type WriteupCountAggregateOutputType = {
    id: number
    gameId: number
    createdAt: number
    updatedAt: number
    formatKey: number
    body: number
    disclosedAi: number
    editorStatus: number
    _all: number
  }


  export type WriteupMinAggregateInputType = {
    id?: true
    gameId?: true
    createdAt?: true
    updatedAt?: true
    formatKey?: true
    body?: true
    disclosedAi?: true
    editorStatus?: true
  }

  export type WriteupMaxAggregateInputType = {
    id?: true
    gameId?: true
    createdAt?: true
    updatedAt?: true
    formatKey?: true
    body?: true
    disclosedAi?: true
    editorStatus?: true
  }

  export type WriteupCountAggregateInputType = {
    id?: true
    gameId?: true
    createdAt?: true
    updatedAt?: true
    formatKey?: true
    body?: true
    disclosedAi?: true
    editorStatus?: true
    _all?: true
  }

  export type WriteupAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Writeup to aggregate.
     */
    where?: WriteupWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Writeups to fetch.
     */
    orderBy?: WriteupOrderByWithRelationInput | WriteupOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: WriteupWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Writeups from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Writeups.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Writeups
    **/
    _count?: true | WriteupCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: WriteupMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: WriteupMaxAggregateInputType
  }

  export type GetWriteupAggregateType<T extends WriteupAggregateArgs> = {
        [P in keyof T & keyof AggregateWriteup]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateWriteup[P]>
      : GetScalarType<T[P], AggregateWriteup[P]>
  }




  export type WriteupGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: WriteupWhereInput
    orderBy?: WriteupOrderByWithAggregationInput | WriteupOrderByWithAggregationInput[]
    by: WriteupScalarFieldEnum[] | WriteupScalarFieldEnum
    having?: WriteupScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: WriteupCountAggregateInputType | true
    _min?: WriteupMinAggregateInputType
    _max?: WriteupMaxAggregateInputType
  }

  export type WriteupGroupByOutputType = {
    id: string
    gameId: string
    createdAt: Date
    updatedAt: Date
    formatKey: string
    body: string
    disclosedAi: boolean
    editorStatus: $Enums.EditorStatus
    _count: WriteupCountAggregateOutputType | null
    _min: WriteupMinAggregateOutputType | null
    _max: WriteupMaxAggregateOutputType | null
  }

  type GetWriteupGroupByPayload<T extends WriteupGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<WriteupGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof WriteupGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], WriteupGroupByOutputType[P]>
            : GetScalarType<T[P], WriteupGroupByOutputType[P]>
        }
      >
    >


  export type WriteupSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    gameId?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    formatKey?: boolean
    body?: boolean
    disclosedAi?: boolean
    editorStatus?: boolean
    game?: boolean | GameDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["writeup"]>

  export type WriteupSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    gameId?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    formatKey?: boolean
    body?: boolean
    disclosedAi?: boolean
    editorStatus?: boolean
    game?: boolean | GameDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["writeup"]>

  export type WriteupSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    gameId?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    formatKey?: boolean
    body?: boolean
    disclosedAi?: boolean
    editorStatus?: boolean
    game?: boolean | GameDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["writeup"]>

  export type WriteupSelectScalar = {
    id?: boolean
    gameId?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    formatKey?: boolean
    body?: boolean
    disclosedAi?: boolean
    editorStatus?: boolean
  }

  export type WriteupOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "gameId" | "createdAt" | "updatedAt" | "formatKey" | "body" | "disclosedAi" | "editorStatus", ExtArgs["result"]["writeup"]>
  export type WriteupInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    game?: boolean | GameDefaultArgs<ExtArgs>
  }
  export type WriteupIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    game?: boolean | GameDefaultArgs<ExtArgs>
  }
  export type WriteupIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    game?: boolean | GameDefaultArgs<ExtArgs>
  }

  export type $WriteupPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Writeup"
    objects: {
      game: Prisma.$GamePayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      gameId: string
      createdAt: Date
      updatedAt: Date
      formatKey: string
      body: string
      disclosedAi: boolean
      editorStatus: $Enums.EditorStatus
    }, ExtArgs["result"]["writeup"]>
    composites: {}
  }

  type WriteupGetPayload<S extends boolean | null | undefined | WriteupDefaultArgs> = $Result.GetResult<Prisma.$WriteupPayload, S>

  type WriteupCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<WriteupFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: WriteupCountAggregateInputType | true
    }

  export interface WriteupDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Writeup'], meta: { name: 'Writeup' } }
    /**
     * Find zero or one Writeup that matches the filter.
     * @param {WriteupFindUniqueArgs} args - Arguments to find a Writeup
     * @example
     * // Get one Writeup
     * const writeup = await prisma.writeup.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends WriteupFindUniqueArgs>(args: SelectSubset<T, WriteupFindUniqueArgs<ExtArgs>>): Prisma__WriteupClient<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Writeup that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {WriteupFindUniqueOrThrowArgs} args - Arguments to find a Writeup
     * @example
     * // Get one Writeup
     * const writeup = await prisma.writeup.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends WriteupFindUniqueOrThrowArgs>(args: SelectSubset<T, WriteupFindUniqueOrThrowArgs<ExtArgs>>): Prisma__WriteupClient<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Writeup that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WriteupFindFirstArgs} args - Arguments to find a Writeup
     * @example
     * // Get one Writeup
     * const writeup = await prisma.writeup.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends WriteupFindFirstArgs>(args?: SelectSubset<T, WriteupFindFirstArgs<ExtArgs>>): Prisma__WriteupClient<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Writeup that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WriteupFindFirstOrThrowArgs} args - Arguments to find a Writeup
     * @example
     * // Get one Writeup
     * const writeup = await prisma.writeup.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends WriteupFindFirstOrThrowArgs>(args?: SelectSubset<T, WriteupFindFirstOrThrowArgs<ExtArgs>>): Prisma__WriteupClient<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Writeups that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WriteupFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Writeups
     * const writeups = await prisma.writeup.findMany()
     * 
     * // Get first 10 Writeups
     * const writeups = await prisma.writeup.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const writeupWithIdOnly = await prisma.writeup.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends WriteupFindManyArgs>(args?: SelectSubset<T, WriteupFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Writeup.
     * @param {WriteupCreateArgs} args - Arguments to create a Writeup.
     * @example
     * // Create one Writeup
     * const Writeup = await prisma.writeup.create({
     *   data: {
     *     // ... data to create a Writeup
     *   }
     * })
     * 
     */
    create<T extends WriteupCreateArgs>(args: SelectSubset<T, WriteupCreateArgs<ExtArgs>>): Prisma__WriteupClient<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Writeups.
     * @param {WriteupCreateManyArgs} args - Arguments to create many Writeups.
     * @example
     * // Create many Writeups
     * const writeup = await prisma.writeup.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends WriteupCreateManyArgs>(args?: SelectSubset<T, WriteupCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Writeups and returns the data saved in the database.
     * @param {WriteupCreateManyAndReturnArgs} args - Arguments to create many Writeups.
     * @example
     * // Create many Writeups
     * const writeup = await prisma.writeup.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Writeups and only return the `id`
     * const writeupWithIdOnly = await prisma.writeup.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends WriteupCreateManyAndReturnArgs>(args?: SelectSubset<T, WriteupCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Writeup.
     * @param {WriteupDeleteArgs} args - Arguments to delete one Writeup.
     * @example
     * // Delete one Writeup
     * const Writeup = await prisma.writeup.delete({
     *   where: {
     *     // ... filter to delete one Writeup
     *   }
     * })
     * 
     */
    delete<T extends WriteupDeleteArgs>(args: SelectSubset<T, WriteupDeleteArgs<ExtArgs>>): Prisma__WriteupClient<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Writeup.
     * @param {WriteupUpdateArgs} args - Arguments to update one Writeup.
     * @example
     * // Update one Writeup
     * const writeup = await prisma.writeup.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends WriteupUpdateArgs>(args: SelectSubset<T, WriteupUpdateArgs<ExtArgs>>): Prisma__WriteupClient<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Writeups.
     * @param {WriteupDeleteManyArgs} args - Arguments to filter Writeups to delete.
     * @example
     * // Delete a few Writeups
     * const { count } = await prisma.writeup.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends WriteupDeleteManyArgs>(args?: SelectSubset<T, WriteupDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Writeups.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WriteupUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Writeups
     * const writeup = await prisma.writeup.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends WriteupUpdateManyArgs>(args: SelectSubset<T, WriteupUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Writeups and returns the data updated in the database.
     * @param {WriteupUpdateManyAndReturnArgs} args - Arguments to update many Writeups.
     * @example
     * // Update many Writeups
     * const writeup = await prisma.writeup.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Writeups and only return the `id`
     * const writeupWithIdOnly = await prisma.writeup.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends WriteupUpdateManyAndReturnArgs>(args: SelectSubset<T, WriteupUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Writeup.
     * @param {WriteupUpsertArgs} args - Arguments to update or create a Writeup.
     * @example
     * // Update or create a Writeup
     * const writeup = await prisma.writeup.upsert({
     *   create: {
     *     // ... data to create a Writeup
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Writeup we want to update
     *   }
     * })
     */
    upsert<T extends WriteupUpsertArgs>(args: SelectSubset<T, WriteupUpsertArgs<ExtArgs>>): Prisma__WriteupClient<$Result.GetResult<Prisma.$WriteupPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Writeups.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WriteupCountArgs} args - Arguments to filter Writeups to count.
     * @example
     * // Count the number of Writeups
     * const count = await prisma.writeup.count({
     *   where: {
     *     // ... the filter for the Writeups we want to count
     *   }
     * })
    **/
    count<T extends WriteupCountArgs>(
      args?: Subset<T, WriteupCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], WriteupCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Writeup.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WriteupAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends WriteupAggregateArgs>(args: Subset<T, WriteupAggregateArgs>): Prisma.PrismaPromise<GetWriteupAggregateType<T>>

    /**
     * Group by Writeup.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {WriteupGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends WriteupGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: WriteupGroupByArgs['orderBy'] }
        : { orderBy?: WriteupGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, WriteupGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetWriteupGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Writeup model
   */
  readonly fields: WriteupFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Writeup.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__WriteupClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    game<T extends GameDefaultArgs<ExtArgs> = {}>(args?: Subset<T, GameDefaultArgs<ExtArgs>>): Prisma__GameClient<$Result.GetResult<Prisma.$GamePayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Writeup model
   */
  interface WriteupFieldRefs {
    readonly id: FieldRef<"Writeup", 'String'>
    readonly gameId: FieldRef<"Writeup", 'String'>
    readonly createdAt: FieldRef<"Writeup", 'DateTime'>
    readonly updatedAt: FieldRef<"Writeup", 'DateTime'>
    readonly formatKey: FieldRef<"Writeup", 'String'>
    readonly body: FieldRef<"Writeup", 'String'>
    readonly disclosedAi: FieldRef<"Writeup", 'Boolean'>
    readonly editorStatus: FieldRef<"Writeup", 'EditorStatus'>
  }
    

  // Custom InputTypes
  /**
   * Writeup findUnique
   */
  export type WriteupFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    /**
     * Filter, which Writeup to fetch.
     */
    where: WriteupWhereUniqueInput
  }

  /**
   * Writeup findUniqueOrThrow
   */
  export type WriteupFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    /**
     * Filter, which Writeup to fetch.
     */
    where: WriteupWhereUniqueInput
  }

  /**
   * Writeup findFirst
   */
  export type WriteupFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    /**
     * Filter, which Writeup to fetch.
     */
    where?: WriteupWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Writeups to fetch.
     */
    orderBy?: WriteupOrderByWithRelationInput | WriteupOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Writeups.
     */
    cursor?: WriteupWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Writeups from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Writeups.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Writeups.
     */
    distinct?: WriteupScalarFieldEnum | WriteupScalarFieldEnum[]
  }

  /**
   * Writeup findFirstOrThrow
   */
  export type WriteupFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    /**
     * Filter, which Writeup to fetch.
     */
    where?: WriteupWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Writeups to fetch.
     */
    orderBy?: WriteupOrderByWithRelationInput | WriteupOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Writeups.
     */
    cursor?: WriteupWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Writeups from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Writeups.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Writeups.
     */
    distinct?: WriteupScalarFieldEnum | WriteupScalarFieldEnum[]
  }

  /**
   * Writeup findMany
   */
  export type WriteupFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    /**
     * Filter, which Writeups to fetch.
     */
    where?: WriteupWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Writeups to fetch.
     */
    orderBy?: WriteupOrderByWithRelationInput | WriteupOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Writeups.
     */
    cursor?: WriteupWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Writeups from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Writeups.
     */
    skip?: number
    distinct?: WriteupScalarFieldEnum | WriteupScalarFieldEnum[]
  }

  /**
   * Writeup create
   */
  export type WriteupCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    /**
     * The data needed to create a Writeup.
     */
    data: XOR<WriteupCreateInput, WriteupUncheckedCreateInput>
  }

  /**
   * Writeup createMany
   */
  export type WriteupCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Writeups.
     */
    data: WriteupCreateManyInput | WriteupCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Writeup createManyAndReturn
   */
  export type WriteupCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * The data used to create many Writeups.
     */
    data: WriteupCreateManyInput | WriteupCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Writeup update
   */
  export type WriteupUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    /**
     * The data needed to update a Writeup.
     */
    data: XOR<WriteupUpdateInput, WriteupUncheckedUpdateInput>
    /**
     * Choose, which Writeup to update.
     */
    where: WriteupWhereUniqueInput
  }

  /**
   * Writeup updateMany
   */
  export type WriteupUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Writeups.
     */
    data: XOR<WriteupUpdateManyMutationInput, WriteupUncheckedUpdateManyInput>
    /**
     * Filter which Writeups to update
     */
    where?: WriteupWhereInput
    /**
     * Limit how many Writeups to update.
     */
    limit?: number
  }

  /**
   * Writeup updateManyAndReturn
   */
  export type WriteupUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * The data used to update Writeups.
     */
    data: XOR<WriteupUpdateManyMutationInput, WriteupUncheckedUpdateManyInput>
    /**
     * Filter which Writeups to update
     */
    where?: WriteupWhereInput
    /**
     * Limit how many Writeups to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Writeup upsert
   */
  export type WriteupUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    /**
     * The filter to search for the Writeup to update in case it exists.
     */
    where: WriteupWhereUniqueInput
    /**
     * In case the Writeup found by the `where` argument doesn't exist, create a new Writeup with this data.
     */
    create: XOR<WriteupCreateInput, WriteupUncheckedCreateInput>
    /**
     * In case the Writeup was found with the provided `where` argument, update it with this data.
     */
    update: XOR<WriteupUpdateInput, WriteupUncheckedUpdateInput>
  }

  /**
   * Writeup delete
   */
  export type WriteupDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
    /**
     * Filter which Writeup to delete.
     */
    where: WriteupWhereUniqueInput
  }

  /**
   * Writeup deleteMany
   */
  export type WriteupDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Writeups to delete
     */
    where?: WriteupWhereInput
    /**
     * Limit how many Writeups to delete.
     */
    limit?: number
  }

  /**
   * Writeup without action
   */
  export type WriteupDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Writeup
     */
    select?: WriteupSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Writeup
     */
    omit?: WriteupOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: WriteupInclude<ExtArgs> | null
  }


  /**
   * Model Injury
   */

  export type AggregateInjury = {
    _count: InjuryCountAggregateOutputType | null
    _min: InjuryMinAggregateOutputType | null
    _max: InjuryMaxAggregateOutputType | null
  }

  export type InjuryMinAggregateOutputType = {
    id: string | null
    teamId: string | null
    date: Date | null
    player: string | null
    status: $Enums.InjuryStatus | null
    note: string | null
    impact: $Enums.InjuryImpact | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type InjuryMaxAggregateOutputType = {
    id: string | null
    teamId: string | null
    date: Date | null
    player: string | null
    status: $Enums.InjuryStatus | null
    note: string | null
    impact: $Enums.InjuryImpact | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type InjuryCountAggregateOutputType = {
    id: number
    teamId: number
    date: number
    player: number
    status: number
    note: number
    impact: number
    createdAt: number
    updatedAt: number
    _all: number
  }


  export type InjuryMinAggregateInputType = {
    id?: true
    teamId?: true
    date?: true
    player?: true
    status?: true
    note?: true
    impact?: true
    createdAt?: true
    updatedAt?: true
  }

  export type InjuryMaxAggregateInputType = {
    id?: true
    teamId?: true
    date?: true
    player?: true
    status?: true
    note?: true
    impact?: true
    createdAt?: true
    updatedAt?: true
  }

  export type InjuryCountAggregateInputType = {
    id?: true
    teamId?: true
    date?: true
    player?: true
    status?: true
    note?: true
    impact?: true
    createdAt?: true
    updatedAt?: true
    _all?: true
  }

  export type InjuryAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Injury to aggregate.
     */
    where?: InjuryWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Injuries to fetch.
     */
    orderBy?: InjuryOrderByWithRelationInput | InjuryOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: InjuryWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Injuries from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Injuries.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Injuries
    **/
    _count?: true | InjuryCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: InjuryMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: InjuryMaxAggregateInputType
  }

  export type GetInjuryAggregateType<T extends InjuryAggregateArgs> = {
        [P in keyof T & keyof AggregateInjury]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateInjury[P]>
      : GetScalarType<T[P], AggregateInjury[P]>
  }




  export type InjuryGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: InjuryWhereInput
    orderBy?: InjuryOrderByWithAggregationInput | InjuryOrderByWithAggregationInput[]
    by: InjuryScalarFieldEnum[] | InjuryScalarFieldEnum
    having?: InjuryScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: InjuryCountAggregateInputType | true
    _min?: InjuryMinAggregateInputType
    _max?: InjuryMaxAggregateInputType
  }

  export type InjuryGroupByOutputType = {
    id: string
    teamId: string
    date: Date
    player: string
    status: $Enums.InjuryStatus
    note: string | null
    impact: $Enums.InjuryImpact | null
    createdAt: Date
    updatedAt: Date
    _count: InjuryCountAggregateOutputType | null
    _min: InjuryMinAggregateOutputType | null
    _max: InjuryMaxAggregateOutputType | null
  }

  type GetInjuryGroupByPayload<T extends InjuryGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<InjuryGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof InjuryGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], InjuryGroupByOutputType[P]>
            : GetScalarType<T[P], InjuryGroupByOutputType[P]>
        }
      >
    >


  export type InjurySelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    teamId?: boolean
    date?: boolean
    player?: boolean
    status?: boolean
    note?: boolean
    impact?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["injury"]>

  export type InjurySelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    teamId?: boolean
    date?: boolean
    player?: boolean
    status?: boolean
    note?: boolean
    impact?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["injury"]>

  export type InjurySelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    teamId?: boolean
    date?: boolean
    player?: boolean
    status?: boolean
    note?: boolean
    impact?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["injury"]>

  export type InjurySelectScalar = {
    id?: boolean
    teamId?: boolean
    date?: boolean
    player?: boolean
    status?: boolean
    note?: boolean
    impact?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }

  export type InjuryOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "teamId" | "date" | "player" | "status" | "note" | "impact" | "createdAt" | "updatedAt", ExtArgs["result"]["injury"]>
  export type InjuryInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }
  export type InjuryIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }
  export type InjuryIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }

  export type $InjuryPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Injury"
    objects: {
      team: Prisma.$TeamPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      teamId: string
      date: Date
      player: string
      status: $Enums.InjuryStatus
      note: string | null
      impact: $Enums.InjuryImpact | null
      createdAt: Date
      updatedAt: Date
    }, ExtArgs["result"]["injury"]>
    composites: {}
  }

  type InjuryGetPayload<S extends boolean | null | undefined | InjuryDefaultArgs> = $Result.GetResult<Prisma.$InjuryPayload, S>

  type InjuryCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<InjuryFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: InjuryCountAggregateInputType | true
    }

  export interface InjuryDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Injury'], meta: { name: 'Injury' } }
    /**
     * Find zero or one Injury that matches the filter.
     * @param {InjuryFindUniqueArgs} args - Arguments to find a Injury
     * @example
     * // Get one Injury
     * const injury = await prisma.injury.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends InjuryFindUniqueArgs>(args: SelectSubset<T, InjuryFindUniqueArgs<ExtArgs>>): Prisma__InjuryClient<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Injury that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {InjuryFindUniqueOrThrowArgs} args - Arguments to find a Injury
     * @example
     * // Get one Injury
     * const injury = await prisma.injury.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends InjuryFindUniqueOrThrowArgs>(args: SelectSubset<T, InjuryFindUniqueOrThrowArgs<ExtArgs>>): Prisma__InjuryClient<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Injury that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {InjuryFindFirstArgs} args - Arguments to find a Injury
     * @example
     * // Get one Injury
     * const injury = await prisma.injury.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends InjuryFindFirstArgs>(args?: SelectSubset<T, InjuryFindFirstArgs<ExtArgs>>): Prisma__InjuryClient<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Injury that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {InjuryFindFirstOrThrowArgs} args - Arguments to find a Injury
     * @example
     * // Get one Injury
     * const injury = await prisma.injury.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends InjuryFindFirstOrThrowArgs>(args?: SelectSubset<T, InjuryFindFirstOrThrowArgs<ExtArgs>>): Prisma__InjuryClient<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Injuries that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {InjuryFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Injuries
     * const injuries = await prisma.injury.findMany()
     * 
     * // Get first 10 Injuries
     * const injuries = await prisma.injury.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const injuryWithIdOnly = await prisma.injury.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends InjuryFindManyArgs>(args?: SelectSubset<T, InjuryFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Injury.
     * @param {InjuryCreateArgs} args - Arguments to create a Injury.
     * @example
     * // Create one Injury
     * const Injury = await prisma.injury.create({
     *   data: {
     *     // ... data to create a Injury
     *   }
     * })
     * 
     */
    create<T extends InjuryCreateArgs>(args: SelectSubset<T, InjuryCreateArgs<ExtArgs>>): Prisma__InjuryClient<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Injuries.
     * @param {InjuryCreateManyArgs} args - Arguments to create many Injuries.
     * @example
     * // Create many Injuries
     * const injury = await prisma.injury.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends InjuryCreateManyArgs>(args?: SelectSubset<T, InjuryCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Injuries and returns the data saved in the database.
     * @param {InjuryCreateManyAndReturnArgs} args - Arguments to create many Injuries.
     * @example
     * // Create many Injuries
     * const injury = await prisma.injury.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Injuries and only return the `id`
     * const injuryWithIdOnly = await prisma.injury.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends InjuryCreateManyAndReturnArgs>(args?: SelectSubset<T, InjuryCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Injury.
     * @param {InjuryDeleteArgs} args - Arguments to delete one Injury.
     * @example
     * // Delete one Injury
     * const Injury = await prisma.injury.delete({
     *   where: {
     *     // ... filter to delete one Injury
     *   }
     * })
     * 
     */
    delete<T extends InjuryDeleteArgs>(args: SelectSubset<T, InjuryDeleteArgs<ExtArgs>>): Prisma__InjuryClient<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Injury.
     * @param {InjuryUpdateArgs} args - Arguments to update one Injury.
     * @example
     * // Update one Injury
     * const injury = await prisma.injury.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends InjuryUpdateArgs>(args: SelectSubset<T, InjuryUpdateArgs<ExtArgs>>): Prisma__InjuryClient<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Injuries.
     * @param {InjuryDeleteManyArgs} args - Arguments to filter Injuries to delete.
     * @example
     * // Delete a few Injuries
     * const { count } = await prisma.injury.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends InjuryDeleteManyArgs>(args?: SelectSubset<T, InjuryDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Injuries.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {InjuryUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Injuries
     * const injury = await prisma.injury.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends InjuryUpdateManyArgs>(args: SelectSubset<T, InjuryUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Injuries and returns the data updated in the database.
     * @param {InjuryUpdateManyAndReturnArgs} args - Arguments to update many Injuries.
     * @example
     * // Update many Injuries
     * const injury = await prisma.injury.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Injuries and only return the `id`
     * const injuryWithIdOnly = await prisma.injury.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends InjuryUpdateManyAndReturnArgs>(args: SelectSubset<T, InjuryUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Injury.
     * @param {InjuryUpsertArgs} args - Arguments to update or create a Injury.
     * @example
     * // Update or create a Injury
     * const injury = await prisma.injury.upsert({
     *   create: {
     *     // ... data to create a Injury
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Injury we want to update
     *   }
     * })
     */
    upsert<T extends InjuryUpsertArgs>(args: SelectSubset<T, InjuryUpsertArgs<ExtArgs>>): Prisma__InjuryClient<$Result.GetResult<Prisma.$InjuryPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Injuries.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {InjuryCountArgs} args - Arguments to filter Injuries to count.
     * @example
     * // Count the number of Injuries
     * const count = await prisma.injury.count({
     *   where: {
     *     // ... the filter for the Injuries we want to count
     *   }
     * })
    **/
    count<T extends InjuryCountArgs>(
      args?: Subset<T, InjuryCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], InjuryCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Injury.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {InjuryAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends InjuryAggregateArgs>(args: Subset<T, InjuryAggregateArgs>): Prisma.PrismaPromise<GetInjuryAggregateType<T>>

    /**
     * Group by Injury.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {InjuryGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends InjuryGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: InjuryGroupByArgs['orderBy'] }
        : { orderBy?: InjuryGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, InjuryGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetInjuryGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Injury model
   */
  readonly fields: InjuryFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Injury.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__InjuryClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    team<T extends TeamDefaultArgs<ExtArgs> = {}>(args?: Subset<T, TeamDefaultArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Injury model
   */
  interface InjuryFieldRefs {
    readonly id: FieldRef<"Injury", 'String'>
    readonly teamId: FieldRef<"Injury", 'String'>
    readonly date: FieldRef<"Injury", 'DateTime'>
    readonly player: FieldRef<"Injury", 'String'>
    readonly status: FieldRef<"Injury", 'InjuryStatus'>
    readonly note: FieldRef<"Injury", 'String'>
    readonly impact: FieldRef<"Injury", 'InjuryImpact'>
    readonly createdAt: FieldRef<"Injury", 'DateTime'>
    readonly updatedAt: FieldRef<"Injury", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * Injury findUnique
   */
  export type InjuryFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    /**
     * Filter, which Injury to fetch.
     */
    where: InjuryWhereUniqueInput
  }

  /**
   * Injury findUniqueOrThrow
   */
  export type InjuryFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    /**
     * Filter, which Injury to fetch.
     */
    where: InjuryWhereUniqueInput
  }

  /**
   * Injury findFirst
   */
  export type InjuryFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    /**
     * Filter, which Injury to fetch.
     */
    where?: InjuryWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Injuries to fetch.
     */
    orderBy?: InjuryOrderByWithRelationInput | InjuryOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Injuries.
     */
    cursor?: InjuryWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Injuries from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Injuries.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Injuries.
     */
    distinct?: InjuryScalarFieldEnum | InjuryScalarFieldEnum[]
  }

  /**
   * Injury findFirstOrThrow
   */
  export type InjuryFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    /**
     * Filter, which Injury to fetch.
     */
    where?: InjuryWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Injuries to fetch.
     */
    orderBy?: InjuryOrderByWithRelationInput | InjuryOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Injuries.
     */
    cursor?: InjuryWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Injuries from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Injuries.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Injuries.
     */
    distinct?: InjuryScalarFieldEnum | InjuryScalarFieldEnum[]
  }

  /**
   * Injury findMany
   */
  export type InjuryFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    /**
     * Filter, which Injuries to fetch.
     */
    where?: InjuryWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Injuries to fetch.
     */
    orderBy?: InjuryOrderByWithRelationInput | InjuryOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Injuries.
     */
    cursor?: InjuryWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Injuries from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Injuries.
     */
    skip?: number
    distinct?: InjuryScalarFieldEnum | InjuryScalarFieldEnum[]
  }

  /**
   * Injury create
   */
  export type InjuryCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    /**
     * The data needed to create a Injury.
     */
    data: XOR<InjuryCreateInput, InjuryUncheckedCreateInput>
  }

  /**
   * Injury createMany
   */
  export type InjuryCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Injuries.
     */
    data: InjuryCreateManyInput | InjuryCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Injury createManyAndReturn
   */
  export type InjuryCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * The data used to create many Injuries.
     */
    data: InjuryCreateManyInput | InjuryCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Injury update
   */
  export type InjuryUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    /**
     * The data needed to update a Injury.
     */
    data: XOR<InjuryUpdateInput, InjuryUncheckedUpdateInput>
    /**
     * Choose, which Injury to update.
     */
    where: InjuryWhereUniqueInput
  }

  /**
   * Injury updateMany
   */
  export type InjuryUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Injuries.
     */
    data: XOR<InjuryUpdateManyMutationInput, InjuryUncheckedUpdateManyInput>
    /**
     * Filter which Injuries to update
     */
    where?: InjuryWhereInput
    /**
     * Limit how many Injuries to update.
     */
    limit?: number
  }

  /**
   * Injury updateManyAndReturn
   */
  export type InjuryUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * The data used to update Injuries.
     */
    data: XOR<InjuryUpdateManyMutationInput, InjuryUncheckedUpdateManyInput>
    /**
     * Filter which Injuries to update
     */
    where?: InjuryWhereInput
    /**
     * Limit how many Injuries to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Injury upsert
   */
  export type InjuryUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    /**
     * The filter to search for the Injury to update in case it exists.
     */
    where: InjuryWhereUniqueInput
    /**
     * In case the Injury found by the `where` argument doesn't exist, create a new Injury with this data.
     */
    create: XOR<InjuryCreateInput, InjuryUncheckedCreateInput>
    /**
     * In case the Injury was found with the provided `where` argument, update it with this data.
     */
    update: XOR<InjuryUpdateInput, InjuryUncheckedUpdateInput>
  }

  /**
   * Injury delete
   */
  export type InjuryDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
    /**
     * Filter which Injury to delete.
     */
    where: InjuryWhereUniqueInput
  }

  /**
   * Injury deleteMany
   */
  export type InjuryDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Injuries to delete
     */
    where?: InjuryWhereInput
    /**
     * Limit how many Injuries to delete.
     */
    limit?: number
  }

  /**
   * Injury without action
   */
  export type InjuryDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Injury
     */
    select?: InjurySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Injury
     */
    omit?: InjuryOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: InjuryInclude<ExtArgs> | null
  }


  /**
   * Model TeamProfileWeekly
   */

  export type AggregateTeamProfileWeekly = {
    _count: TeamProfileWeeklyCountAggregateOutputType | null
    _avg: TeamProfileWeeklyAvgAggregateOutputType | null
    _sum: TeamProfileWeeklySumAggregateOutputType | null
    _min: TeamProfileWeeklyMinAggregateOutputType | null
    _max: TeamProfileWeeklyMaxAggregateOutputType | null
  }

  export type TeamProfileWeeklyAvgAggregateOutputType = {
    tempoRank: number | null
    offPpp: number | null
    defPpp: number | null
  }

  export type TeamProfileWeeklySumAggregateOutputType = {
    tempoRank: number | null
    offPpp: number | null
    defPpp: number | null
  }

  export type TeamProfileWeeklyMinAggregateOutputType = {
    id: string | null
    teamId: string | null
    weekStart: Date | null
    summary: string | null
    tempoRank: number | null
    offPpp: number | null
    defPpp: number | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type TeamProfileWeeklyMaxAggregateOutputType = {
    id: string | null
    teamId: string | null
    weekStart: Date | null
    summary: string | null
    tempoRank: number | null
    offPpp: number | null
    defPpp: number | null
    createdAt: Date | null
    updatedAt: Date | null
  }

  export type TeamProfileWeeklyCountAggregateOutputType = {
    id: number
    teamId: number
    weekStart: number
    summary: number
    tempoRank: number
    offPpp: number
    defPpp: number
    createdAt: number
    updatedAt: number
    _all: number
  }


  export type TeamProfileWeeklyAvgAggregateInputType = {
    tempoRank?: true
    offPpp?: true
    defPpp?: true
  }

  export type TeamProfileWeeklySumAggregateInputType = {
    tempoRank?: true
    offPpp?: true
    defPpp?: true
  }

  export type TeamProfileWeeklyMinAggregateInputType = {
    id?: true
    teamId?: true
    weekStart?: true
    summary?: true
    tempoRank?: true
    offPpp?: true
    defPpp?: true
    createdAt?: true
    updatedAt?: true
  }

  export type TeamProfileWeeklyMaxAggregateInputType = {
    id?: true
    teamId?: true
    weekStart?: true
    summary?: true
    tempoRank?: true
    offPpp?: true
    defPpp?: true
    createdAt?: true
    updatedAt?: true
  }

  export type TeamProfileWeeklyCountAggregateInputType = {
    id?: true
    teamId?: true
    weekStart?: true
    summary?: true
    tempoRank?: true
    offPpp?: true
    defPpp?: true
    createdAt?: true
    updatedAt?: true
    _all?: true
  }

  export type TeamProfileWeeklyAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which TeamProfileWeekly to aggregate.
     */
    where?: TeamProfileWeeklyWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TeamProfileWeeklies to fetch.
     */
    orderBy?: TeamProfileWeeklyOrderByWithRelationInput | TeamProfileWeeklyOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: TeamProfileWeeklyWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TeamProfileWeeklies from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TeamProfileWeeklies.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned TeamProfileWeeklies
    **/
    _count?: true | TeamProfileWeeklyCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to average
    **/
    _avg?: TeamProfileWeeklyAvgAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to sum
    **/
    _sum?: TeamProfileWeeklySumAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: TeamProfileWeeklyMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: TeamProfileWeeklyMaxAggregateInputType
  }

  export type GetTeamProfileWeeklyAggregateType<T extends TeamProfileWeeklyAggregateArgs> = {
        [P in keyof T & keyof AggregateTeamProfileWeekly]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateTeamProfileWeekly[P]>
      : GetScalarType<T[P], AggregateTeamProfileWeekly[P]>
  }




  export type TeamProfileWeeklyGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TeamProfileWeeklyWhereInput
    orderBy?: TeamProfileWeeklyOrderByWithAggregationInput | TeamProfileWeeklyOrderByWithAggregationInput[]
    by: TeamProfileWeeklyScalarFieldEnum[] | TeamProfileWeeklyScalarFieldEnum
    having?: TeamProfileWeeklyScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: TeamProfileWeeklyCountAggregateInputType | true
    _avg?: TeamProfileWeeklyAvgAggregateInputType
    _sum?: TeamProfileWeeklySumAggregateInputType
    _min?: TeamProfileWeeklyMinAggregateInputType
    _max?: TeamProfileWeeklyMaxAggregateInputType
  }

  export type TeamProfileWeeklyGroupByOutputType = {
    id: string
    teamId: string
    weekStart: Date
    summary: string
    tempoRank: number | null
    offPpp: number | null
    defPpp: number | null
    createdAt: Date
    updatedAt: Date
    _count: TeamProfileWeeklyCountAggregateOutputType | null
    _avg: TeamProfileWeeklyAvgAggregateOutputType | null
    _sum: TeamProfileWeeklySumAggregateOutputType | null
    _min: TeamProfileWeeklyMinAggregateOutputType | null
    _max: TeamProfileWeeklyMaxAggregateOutputType | null
  }

  type GetTeamProfileWeeklyGroupByPayload<T extends TeamProfileWeeklyGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<TeamProfileWeeklyGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof TeamProfileWeeklyGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], TeamProfileWeeklyGroupByOutputType[P]>
            : GetScalarType<T[P], TeamProfileWeeklyGroupByOutputType[P]>
        }
      >
    >


  export type TeamProfileWeeklySelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    teamId?: boolean
    weekStart?: boolean
    summary?: boolean
    tempoRank?: boolean
    offPpp?: boolean
    defPpp?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["teamProfileWeekly"]>

  export type TeamProfileWeeklySelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    teamId?: boolean
    weekStart?: boolean
    summary?: boolean
    tempoRank?: boolean
    offPpp?: boolean
    defPpp?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["teamProfileWeekly"]>

  export type TeamProfileWeeklySelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    teamId?: boolean
    weekStart?: boolean
    summary?: boolean
    tempoRank?: boolean
    offPpp?: boolean
    defPpp?: boolean
    createdAt?: boolean
    updatedAt?: boolean
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["teamProfileWeekly"]>

  export type TeamProfileWeeklySelectScalar = {
    id?: boolean
    teamId?: boolean
    weekStart?: boolean
    summary?: boolean
    tempoRank?: boolean
    offPpp?: boolean
    defPpp?: boolean
    createdAt?: boolean
    updatedAt?: boolean
  }

  export type TeamProfileWeeklyOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "teamId" | "weekStart" | "summary" | "tempoRank" | "offPpp" | "defPpp" | "createdAt" | "updatedAt", ExtArgs["result"]["teamProfileWeekly"]>
  export type TeamProfileWeeklyInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }
  export type TeamProfileWeeklyIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }
  export type TeamProfileWeeklyIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    team?: boolean | TeamDefaultArgs<ExtArgs>
  }

  export type $TeamProfileWeeklyPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "TeamProfileWeekly"
    objects: {
      team: Prisma.$TeamPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      teamId: string
      weekStart: Date
      summary: string
      tempoRank: number | null
      offPpp: number | null
      defPpp: number | null
      createdAt: Date
      updatedAt: Date
    }, ExtArgs["result"]["teamProfileWeekly"]>
    composites: {}
  }

  type TeamProfileWeeklyGetPayload<S extends boolean | null | undefined | TeamProfileWeeklyDefaultArgs> = $Result.GetResult<Prisma.$TeamProfileWeeklyPayload, S>

  type TeamProfileWeeklyCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<TeamProfileWeeklyFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: TeamProfileWeeklyCountAggregateInputType | true
    }

  export interface TeamProfileWeeklyDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['TeamProfileWeekly'], meta: { name: 'TeamProfileWeekly' } }
    /**
     * Find zero or one TeamProfileWeekly that matches the filter.
     * @param {TeamProfileWeeklyFindUniqueArgs} args - Arguments to find a TeamProfileWeekly
     * @example
     * // Get one TeamProfileWeekly
     * const teamProfileWeekly = await prisma.teamProfileWeekly.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends TeamProfileWeeklyFindUniqueArgs>(args: SelectSubset<T, TeamProfileWeeklyFindUniqueArgs<ExtArgs>>): Prisma__TeamProfileWeeklyClient<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one TeamProfileWeekly that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {TeamProfileWeeklyFindUniqueOrThrowArgs} args - Arguments to find a TeamProfileWeekly
     * @example
     * // Get one TeamProfileWeekly
     * const teamProfileWeekly = await prisma.teamProfileWeekly.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends TeamProfileWeeklyFindUniqueOrThrowArgs>(args: SelectSubset<T, TeamProfileWeeklyFindUniqueOrThrowArgs<ExtArgs>>): Prisma__TeamProfileWeeklyClient<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first TeamProfileWeekly that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamProfileWeeklyFindFirstArgs} args - Arguments to find a TeamProfileWeekly
     * @example
     * // Get one TeamProfileWeekly
     * const teamProfileWeekly = await prisma.teamProfileWeekly.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends TeamProfileWeeklyFindFirstArgs>(args?: SelectSubset<T, TeamProfileWeeklyFindFirstArgs<ExtArgs>>): Prisma__TeamProfileWeeklyClient<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first TeamProfileWeekly that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamProfileWeeklyFindFirstOrThrowArgs} args - Arguments to find a TeamProfileWeekly
     * @example
     * // Get one TeamProfileWeekly
     * const teamProfileWeekly = await prisma.teamProfileWeekly.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends TeamProfileWeeklyFindFirstOrThrowArgs>(args?: SelectSubset<T, TeamProfileWeeklyFindFirstOrThrowArgs<ExtArgs>>): Prisma__TeamProfileWeeklyClient<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more TeamProfileWeeklies that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamProfileWeeklyFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all TeamProfileWeeklies
     * const teamProfileWeeklies = await prisma.teamProfileWeekly.findMany()
     * 
     * // Get first 10 TeamProfileWeeklies
     * const teamProfileWeeklies = await prisma.teamProfileWeekly.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const teamProfileWeeklyWithIdOnly = await prisma.teamProfileWeekly.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends TeamProfileWeeklyFindManyArgs>(args?: SelectSubset<T, TeamProfileWeeklyFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a TeamProfileWeekly.
     * @param {TeamProfileWeeklyCreateArgs} args - Arguments to create a TeamProfileWeekly.
     * @example
     * // Create one TeamProfileWeekly
     * const TeamProfileWeekly = await prisma.teamProfileWeekly.create({
     *   data: {
     *     // ... data to create a TeamProfileWeekly
     *   }
     * })
     * 
     */
    create<T extends TeamProfileWeeklyCreateArgs>(args: SelectSubset<T, TeamProfileWeeklyCreateArgs<ExtArgs>>): Prisma__TeamProfileWeeklyClient<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many TeamProfileWeeklies.
     * @param {TeamProfileWeeklyCreateManyArgs} args - Arguments to create many TeamProfileWeeklies.
     * @example
     * // Create many TeamProfileWeeklies
     * const teamProfileWeekly = await prisma.teamProfileWeekly.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends TeamProfileWeeklyCreateManyArgs>(args?: SelectSubset<T, TeamProfileWeeklyCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many TeamProfileWeeklies and returns the data saved in the database.
     * @param {TeamProfileWeeklyCreateManyAndReturnArgs} args - Arguments to create many TeamProfileWeeklies.
     * @example
     * // Create many TeamProfileWeeklies
     * const teamProfileWeekly = await prisma.teamProfileWeekly.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many TeamProfileWeeklies and only return the `id`
     * const teamProfileWeeklyWithIdOnly = await prisma.teamProfileWeekly.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends TeamProfileWeeklyCreateManyAndReturnArgs>(args?: SelectSubset<T, TeamProfileWeeklyCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a TeamProfileWeekly.
     * @param {TeamProfileWeeklyDeleteArgs} args - Arguments to delete one TeamProfileWeekly.
     * @example
     * // Delete one TeamProfileWeekly
     * const TeamProfileWeekly = await prisma.teamProfileWeekly.delete({
     *   where: {
     *     // ... filter to delete one TeamProfileWeekly
     *   }
     * })
     * 
     */
    delete<T extends TeamProfileWeeklyDeleteArgs>(args: SelectSubset<T, TeamProfileWeeklyDeleteArgs<ExtArgs>>): Prisma__TeamProfileWeeklyClient<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one TeamProfileWeekly.
     * @param {TeamProfileWeeklyUpdateArgs} args - Arguments to update one TeamProfileWeekly.
     * @example
     * // Update one TeamProfileWeekly
     * const teamProfileWeekly = await prisma.teamProfileWeekly.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends TeamProfileWeeklyUpdateArgs>(args: SelectSubset<T, TeamProfileWeeklyUpdateArgs<ExtArgs>>): Prisma__TeamProfileWeeklyClient<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more TeamProfileWeeklies.
     * @param {TeamProfileWeeklyDeleteManyArgs} args - Arguments to filter TeamProfileWeeklies to delete.
     * @example
     * // Delete a few TeamProfileWeeklies
     * const { count } = await prisma.teamProfileWeekly.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends TeamProfileWeeklyDeleteManyArgs>(args?: SelectSubset<T, TeamProfileWeeklyDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more TeamProfileWeeklies.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamProfileWeeklyUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many TeamProfileWeeklies
     * const teamProfileWeekly = await prisma.teamProfileWeekly.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends TeamProfileWeeklyUpdateManyArgs>(args: SelectSubset<T, TeamProfileWeeklyUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more TeamProfileWeeklies and returns the data updated in the database.
     * @param {TeamProfileWeeklyUpdateManyAndReturnArgs} args - Arguments to update many TeamProfileWeeklies.
     * @example
     * // Update many TeamProfileWeeklies
     * const teamProfileWeekly = await prisma.teamProfileWeekly.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more TeamProfileWeeklies and only return the `id`
     * const teamProfileWeeklyWithIdOnly = await prisma.teamProfileWeekly.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends TeamProfileWeeklyUpdateManyAndReturnArgs>(args: SelectSubset<T, TeamProfileWeeklyUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one TeamProfileWeekly.
     * @param {TeamProfileWeeklyUpsertArgs} args - Arguments to update or create a TeamProfileWeekly.
     * @example
     * // Update or create a TeamProfileWeekly
     * const teamProfileWeekly = await prisma.teamProfileWeekly.upsert({
     *   create: {
     *     // ... data to create a TeamProfileWeekly
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the TeamProfileWeekly we want to update
     *   }
     * })
     */
    upsert<T extends TeamProfileWeeklyUpsertArgs>(args: SelectSubset<T, TeamProfileWeeklyUpsertArgs<ExtArgs>>): Prisma__TeamProfileWeeklyClient<$Result.GetResult<Prisma.$TeamProfileWeeklyPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of TeamProfileWeeklies.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamProfileWeeklyCountArgs} args - Arguments to filter TeamProfileWeeklies to count.
     * @example
     * // Count the number of TeamProfileWeeklies
     * const count = await prisma.teamProfileWeekly.count({
     *   where: {
     *     // ... the filter for the TeamProfileWeeklies we want to count
     *   }
     * })
    **/
    count<T extends TeamProfileWeeklyCountArgs>(
      args?: Subset<T, TeamProfileWeeklyCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], TeamProfileWeeklyCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a TeamProfileWeekly.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamProfileWeeklyAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends TeamProfileWeeklyAggregateArgs>(args: Subset<T, TeamProfileWeeklyAggregateArgs>): Prisma.PrismaPromise<GetTeamProfileWeeklyAggregateType<T>>

    /**
     * Group by TeamProfileWeekly.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TeamProfileWeeklyGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends TeamProfileWeeklyGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: TeamProfileWeeklyGroupByArgs['orderBy'] }
        : { orderBy?: TeamProfileWeeklyGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, TeamProfileWeeklyGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetTeamProfileWeeklyGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the TeamProfileWeekly model
   */
  readonly fields: TeamProfileWeeklyFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for TeamProfileWeekly.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__TeamProfileWeeklyClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    team<T extends TeamDefaultArgs<ExtArgs> = {}>(args?: Subset<T, TeamDefaultArgs<ExtArgs>>): Prisma__TeamClient<$Result.GetResult<Prisma.$TeamPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the TeamProfileWeekly model
   */
  interface TeamProfileWeeklyFieldRefs {
    readonly id: FieldRef<"TeamProfileWeekly", 'String'>
    readonly teamId: FieldRef<"TeamProfileWeekly", 'String'>
    readonly weekStart: FieldRef<"TeamProfileWeekly", 'DateTime'>
    readonly summary: FieldRef<"TeamProfileWeekly", 'String'>
    readonly tempoRank: FieldRef<"TeamProfileWeekly", 'Int'>
    readonly offPpp: FieldRef<"TeamProfileWeekly", 'Float'>
    readonly defPpp: FieldRef<"TeamProfileWeekly", 'Float'>
    readonly createdAt: FieldRef<"TeamProfileWeekly", 'DateTime'>
    readonly updatedAt: FieldRef<"TeamProfileWeekly", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * TeamProfileWeekly findUnique
   */
  export type TeamProfileWeeklyFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    /**
     * Filter, which TeamProfileWeekly to fetch.
     */
    where: TeamProfileWeeklyWhereUniqueInput
  }

  /**
   * TeamProfileWeekly findUniqueOrThrow
   */
  export type TeamProfileWeeklyFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    /**
     * Filter, which TeamProfileWeekly to fetch.
     */
    where: TeamProfileWeeklyWhereUniqueInput
  }

  /**
   * TeamProfileWeekly findFirst
   */
  export type TeamProfileWeeklyFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    /**
     * Filter, which TeamProfileWeekly to fetch.
     */
    where?: TeamProfileWeeklyWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TeamProfileWeeklies to fetch.
     */
    orderBy?: TeamProfileWeeklyOrderByWithRelationInput | TeamProfileWeeklyOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for TeamProfileWeeklies.
     */
    cursor?: TeamProfileWeeklyWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TeamProfileWeeklies from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TeamProfileWeeklies.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of TeamProfileWeeklies.
     */
    distinct?: TeamProfileWeeklyScalarFieldEnum | TeamProfileWeeklyScalarFieldEnum[]
  }

  /**
   * TeamProfileWeekly findFirstOrThrow
   */
  export type TeamProfileWeeklyFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    /**
     * Filter, which TeamProfileWeekly to fetch.
     */
    where?: TeamProfileWeeklyWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TeamProfileWeeklies to fetch.
     */
    orderBy?: TeamProfileWeeklyOrderByWithRelationInput | TeamProfileWeeklyOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for TeamProfileWeeklies.
     */
    cursor?: TeamProfileWeeklyWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TeamProfileWeeklies from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TeamProfileWeeklies.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of TeamProfileWeeklies.
     */
    distinct?: TeamProfileWeeklyScalarFieldEnum | TeamProfileWeeklyScalarFieldEnum[]
  }

  /**
   * TeamProfileWeekly findMany
   */
  export type TeamProfileWeeklyFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    /**
     * Filter, which TeamProfileWeeklies to fetch.
     */
    where?: TeamProfileWeeklyWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of TeamProfileWeeklies to fetch.
     */
    orderBy?: TeamProfileWeeklyOrderByWithRelationInput | TeamProfileWeeklyOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing TeamProfileWeeklies.
     */
    cursor?: TeamProfileWeeklyWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` TeamProfileWeeklies from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` TeamProfileWeeklies.
     */
    skip?: number
    distinct?: TeamProfileWeeklyScalarFieldEnum | TeamProfileWeeklyScalarFieldEnum[]
  }

  /**
   * TeamProfileWeekly create
   */
  export type TeamProfileWeeklyCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    /**
     * The data needed to create a TeamProfileWeekly.
     */
    data: XOR<TeamProfileWeeklyCreateInput, TeamProfileWeeklyUncheckedCreateInput>
  }

  /**
   * TeamProfileWeekly createMany
   */
  export type TeamProfileWeeklyCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many TeamProfileWeeklies.
     */
    data: TeamProfileWeeklyCreateManyInput | TeamProfileWeeklyCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * TeamProfileWeekly createManyAndReturn
   */
  export type TeamProfileWeeklyCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * The data used to create many TeamProfileWeeklies.
     */
    data: TeamProfileWeeklyCreateManyInput | TeamProfileWeeklyCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * TeamProfileWeekly update
   */
  export type TeamProfileWeeklyUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    /**
     * The data needed to update a TeamProfileWeekly.
     */
    data: XOR<TeamProfileWeeklyUpdateInput, TeamProfileWeeklyUncheckedUpdateInput>
    /**
     * Choose, which TeamProfileWeekly to update.
     */
    where: TeamProfileWeeklyWhereUniqueInput
  }

  /**
   * TeamProfileWeekly updateMany
   */
  export type TeamProfileWeeklyUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update TeamProfileWeeklies.
     */
    data: XOR<TeamProfileWeeklyUpdateManyMutationInput, TeamProfileWeeklyUncheckedUpdateManyInput>
    /**
     * Filter which TeamProfileWeeklies to update
     */
    where?: TeamProfileWeeklyWhereInput
    /**
     * Limit how many TeamProfileWeeklies to update.
     */
    limit?: number
  }

  /**
   * TeamProfileWeekly updateManyAndReturn
   */
  export type TeamProfileWeeklyUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * The data used to update TeamProfileWeeklies.
     */
    data: XOR<TeamProfileWeeklyUpdateManyMutationInput, TeamProfileWeeklyUncheckedUpdateManyInput>
    /**
     * Filter which TeamProfileWeeklies to update
     */
    where?: TeamProfileWeeklyWhereInput
    /**
     * Limit how many TeamProfileWeeklies to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * TeamProfileWeekly upsert
   */
  export type TeamProfileWeeklyUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    /**
     * The filter to search for the TeamProfileWeekly to update in case it exists.
     */
    where: TeamProfileWeeklyWhereUniqueInput
    /**
     * In case the TeamProfileWeekly found by the `where` argument doesn't exist, create a new TeamProfileWeekly with this data.
     */
    create: XOR<TeamProfileWeeklyCreateInput, TeamProfileWeeklyUncheckedCreateInput>
    /**
     * In case the TeamProfileWeekly was found with the provided `where` argument, update it with this data.
     */
    update: XOR<TeamProfileWeeklyUpdateInput, TeamProfileWeeklyUncheckedUpdateInput>
  }

  /**
   * TeamProfileWeekly delete
   */
  export type TeamProfileWeeklyDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
    /**
     * Filter which TeamProfileWeekly to delete.
     */
    where: TeamProfileWeeklyWhereUniqueInput
  }

  /**
   * TeamProfileWeekly deleteMany
   */
  export type TeamProfileWeeklyDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which TeamProfileWeeklies to delete
     */
    where?: TeamProfileWeeklyWhereInput
    /**
     * Limit how many TeamProfileWeeklies to delete.
     */
    limit?: number
  }

  /**
   * TeamProfileWeekly without action
   */
  export type TeamProfileWeeklyDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the TeamProfileWeekly
     */
    select?: TeamProfileWeeklySelect<ExtArgs> | null
    /**
     * Omit specific fields from the TeamProfileWeekly
     */
    omit?: TeamProfileWeeklyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TeamProfileWeeklyInclude<ExtArgs> | null
  }


  /**
   * Enums
   */

  export const TransactionIsolationLevel: {
    ReadUncommitted: 'ReadUncommitted',
    ReadCommitted: 'ReadCommitted',
    RepeatableRead: 'RepeatableRead',
    Serializable: 'Serializable'
  };

  export type TransactionIsolationLevel = (typeof TransactionIsolationLevel)[keyof typeof TransactionIsolationLevel]


  export const UserScalarFieldEnum: {
    id: 'id',
    email: 'email',
    emailVerified: 'emailVerified',
    name: 'name',
    password: 'password',
    image: 'image',
    role: 'role',
    subscriptionStatus: 'subscriptionStatus',
    subscriptionPlan: 'subscriptionPlan',
    subscriptionStart: 'subscriptionStart',
    subscriptionEnd: 'subscriptionEnd',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt'
  };

  export type UserScalarFieldEnum = (typeof UserScalarFieldEnum)[keyof typeof UserScalarFieldEnum]


  export const AccountScalarFieldEnum: {
    id: 'id',
    userId: 'userId',
    type: 'type',
    provider: 'provider',
    providerAccountId: 'providerAccountId',
    refresh_token: 'refresh_token',
    access_token: 'access_token',
    expires_at: 'expires_at',
    token_type: 'token_type',
    scope: 'scope',
    id_token: 'id_token',
    session_state: 'session_state'
  };

  export type AccountScalarFieldEnum = (typeof AccountScalarFieldEnum)[keyof typeof AccountScalarFieldEnum]


  export const SessionScalarFieldEnum: {
    id: 'id',
    sessionToken: 'sessionToken',
    userId: 'userId',
    expires: 'expires'
  };

  export type SessionScalarFieldEnum = (typeof SessionScalarFieldEnum)[keyof typeof SessionScalarFieldEnum]


  export const VerificationTokenScalarFieldEnum: {
    identifier: 'identifier',
    token: 'token',
    expires: 'expires'
  };

  export type VerificationTokenScalarFieldEnum = (typeof VerificationTokenScalarFieldEnum)[keyof typeof VerificationTokenScalarFieldEnum]


  export const SportScalarFieldEnum: {
    id: 'id',
    key: 'key',
    name: 'name',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt'
  };

  export type SportScalarFieldEnum = (typeof SportScalarFieldEnum)[keyof typeof SportScalarFieldEnum]


  export const TeamScalarFieldEnum: {
    id: 'id',
    sportId: 'sportId',
    name: 'name',
    slug: 'slug',
    abbr: 'abbr',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt'
  };

  export type TeamScalarFieldEnum = (typeof TeamScalarFieldEnum)[keyof typeof TeamScalarFieldEnum]


  export const GameScalarFieldEnum: {
    id: 'id',
    sportId: 'sportId',
    date: 'date',
    slug: 'slug',
    homeTeamId: 'homeTeamId',
    awayTeamId: 'awayTeamId',
    startTime: 'startTime',
    venue: 'venue',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt'
  };

  export type GameScalarFieldEnum = (typeof GameScalarFieldEnum)[keyof typeof GameScalarFieldEnum]


  export const MarketSnapshotScalarFieldEnum: {
    id: 'id',
    gameId: 'gameId',
    capturedAt: 'capturedAt',
    openSpreadHome: 'openSpreadHome',
    currentSpreadHome: 'currentSpreadHome',
    openTotal: 'openTotal',
    currentTotal: 'currentTotal',
    bestSpreadHome: 'bestSpreadHome',
    bestSpreadBook: 'bestSpreadBook',
    bestTotal: 'bestTotal',
    bestTotalBook: 'bestTotalBook',
    spreadDispersion: 'spreadDispersion',
    totalDispersion: 'totalDispersion'
  };

  export type MarketSnapshotScalarFieldEnum = (typeof MarketSnapshotScalarFieldEnum)[keyof typeof MarketSnapshotScalarFieldEnum]


  export const BookLineScalarFieldEnum: {
    id: 'id',
    marketId: 'marketId',
    book: 'book',
    capturedAt: 'capturedAt',
    spreadHome: 'spreadHome',
    spreadAway: 'spreadAway',
    total: 'total'
  };

  export type BookLineScalarFieldEnum = (typeof BookLineScalarFieldEnum)[keyof typeof BookLineScalarFieldEnum]


  export const ModelProjectionScalarFieldEnum: {
    id: 'id',
    gameId: 'gameId',
    version: 'version',
    computedAt: 'computedAt',
    projSpreadHome: 'projSpreadHome',
    projTotal: 'projTotal'
  };

  export type ModelProjectionScalarFieldEnum = (typeof ModelProjectionScalarFieldEnum)[keyof typeof ModelProjectionScalarFieldEnum]


  export const WriteupScalarFieldEnum: {
    id: 'id',
    gameId: 'gameId',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt',
    formatKey: 'formatKey',
    body: 'body',
    disclosedAi: 'disclosedAi',
    editorStatus: 'editorStatus'
  };

  export type WriteupScalarFieldEnum = (typeof WriteupScalarFieldEnum)[keyof typeof WriteupScalarFieldEnum]


  export const InjuryScalarFieldEnum: {
    id: 'id',
    teamId: 'teamId',
    date: 'date',
    player: 'player',
    status: 'status',
    note: 'note',
    impact: 'impact',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt'
  };

  export type InjuryScalarFieldEnum = (typeof InjuryScalarFieldEnum)[keyof typeof InjuryScalarFieldEnum]


  export const TeamProfileWeeklyScalarFieldEnum: {
    id: 'id',
    teamId: 'teamId',
    weekStart: 'weekStart',
    summary: 'summary',
    tempoRank: 'tempoRank',
    offPpp: 'offPpp',
    defPpp: 'defPpp',
    createdAt: 'createdAt',
    updatedAt: 'updatedAt'
  };

  export type TeamProfileWeeklyScalarFieldEnum = (typeof TeamProfileWeeklyScalarFieldEnum)[keyof typeof TeamProfileWeeklyScalarFieldEnum]


  export const SortOrder: {
    asc: 'asc',
    desc: 'desc'
  };

  export type SortOrder = (typeof SortOrder)[keyof typeof SortOrder]


  export const QueryMode: {
    default: 'default',
    insensitive: 'insensitive'
  };

  export type QueryMode = (typeof QueryMode)[keyof typeof QueryMode]


  export const NullsOrder: {
    first: 'first',
    last: 'last'
  };

  export type NullsOrder = (typeof NullsOrder)[keyof typeof NullsOrder]


  /**
   * Field references
   */


  /**
   * Reference to a field of type 'String'
   */
  export type StringFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'String'>
    


  /**
   * Reference to a field of type 'String[]'
   */
  export type ListStringFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'String[]'>
    


  /**
   * Reference to a field of type 'DateTime'
   */
  export type DateTimeFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'DateTime'>
    


  /**
   * Reference to a field of type 'DateTime[]'
   */
  export type ListDateTimeFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'DateTime[]'>
    


  /**
   * Reference to a field of type 'UserRole'
   */
  export type EnumUserRoleFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'UserRole'>
    


  /**
   * Reference to a field of type 'UserRole[]'
   */
  export type ListEnumUserRoleFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'UserRole[]'>
    


  /**
   * Reference to a field of type 'SubscriptionStatus'
   */
  export type EnumSubscriptionStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'SubscriptionStatus'>
    


  /**
   * Reference to a field of type 'SubscriptionStatus[]'
   */
  export type ListEnumSubscriptionStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'SubscriptionStatus[]'>
    


  /**
   * Reference to a field of type 'Int'
   */
  export type IntFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Int'>
    


  /**
   * Reference to a field of type 'Int[]'
   */
  export type ListIntFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Int[]'>
    


  /**
   * Reference to a field of type 'Float'
   */
  export type FloatFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Float'>
    


  /**
   * Reference to a field of type 'Float[]'
   */
  export type ListFloatFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Float[]'>
    


  /**
   * Reference to a field of type 'Boolean'
   */
  export type BooleanFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Boolean'>
    


  /**
   * Reference to a field of type 'EditorStatus'
   */
  export type EnumEditorStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'EditorStatus'>
    


  /**
   * Reference to a field of type 'EditorStatus[]'
   */
  export type ListEnumEditorStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'EditorStatus[]'>
    


  /**
   * Reference to a field of type 'InjuryStatus'
   */
  export type EnumInjuryStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'InjuryStatus'>
    


  /**
   * Reference to a field of type 'InjuryStatus[]'
   */
  export type ListEnumInjuryStatusFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'InjuryStatus[]'>
    


  /**
   * Reference to a field of type 'InjuryImpact'
   */
  export type EnumInjuryImpactFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'InjuryImpact'>
    


  /**
   * Reference to a field of type 'InjuryImpact[]'
   */
  export type ListEnumInjuryImpactFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'InjuryImpact[]'>
    
  /**
   * Deep Input Types
   */


  export type UserWhereInput = {
    AND?: UserWhereInput | UserWhereInput[]
    OR?: UserWhereInput[]
    NOT?: UserWhereInput | UserWhereInput[]
    id?: StringFilter<"User"> | string
    email?: StringFilter<"User"> | string
    emailVerified?: DateTimeNullableFilter<"User"> | Date | string | null
    name?: StringNullableFilter<"User"> | string | null
    password?: StringNullableFilter<"User"> | string | null
    image?: StringNullableFilter<"User"> | string | null
    role?: EnumUserRoleFilter<"User"> | $Enums.UserRole
    subscriptionStatus?: EnumSubscriptionStatusNullableFilter<"User"> | $Enums.SubscriptionStatus | null
    subscriptionPlan?: StringNullableFilter<"User"> | string | null
    subscriptionStart?: DateTimeNullableFilter<"User"> | Date | string | null
    subscriptionEnd?: DateTimeNullableFilter<"User"> | Date | string | null
    createdAt?: DateTimeFilter<"User"> | Date | string
    updatedAt?: DateTimeFilter<"User"> | Date | string
    accounts?: AccountListRelationFilter
    sessions?: SessionListRelationFilter
  }

  export type UserOrderByWithRelationInput = {
    id?: SortOrder
    email?: SortOrder
    emailVerified?: SortOrderInput | SortOrder
    name?: SortOrderInput | SortOrder
    password?: SortOrderInput | SortOrder
    image?: SortOrderInput | SortOrder
    role?: SortOrder
    subscriptionStatus?: SortOrderInput | SortOrder
    subscriptionPlan?: SortOrderInput | SortOrder
    subscriptionStart?: SortOrderInput | SortOrder
    subscriptionEnd?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    accounts?: AccountOrderByRelationAggregateInput
    sessions?: SessionOrderByRelationAggregateInput
  }

  export type UserWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    email?: string
    AND?: UserWhereInput | UserWhereInput[]
    OR?: UserWhereInput[]
    NOT?: UserWhereInput | UserWhereInput[]
    emailVerified?: DateTimeNullableFilter<"User"> | Date | string | null
    name?: StringNullableFilter<"User"> | string | null
    password?: StringNullableFilter<"User"> | string | null
    image?: StringNullableFilter<"User"> | string | null
    role?: EnumUserRoleFilter<"User"> | $Enums.UserRole
    subscriptionStatus?: EnumSubscriptionStatusNullableFilter<"User"> | $Enums.SubscriptionStatus | null
    subscriptionPlan?: StringNullableFilter<"User"> | string | null
    subscriptionStart?: DateTimeNullableFilter<"User"> | Date | string | null
    subscriptionEnd?: DateTimeNullableFilter<"User"> | Date | string | null
    createdAt?: DateTimeFilter<"User"> | Date | string
    updatedAt?: DateTimeFilter<"User"> | Date | string
    accounts?: AccountListRelationFilter
    sessions?: SessionListRelationFilter
  }, "id" | "email">

  export type UserOrderByWithAggregationInput = {
    id?: SortOrder
    email?: SortOrder
    emailVerified?: SortOrderInput | SortOrder
    name?: SortOrderInput | SortOrder
    password?: SortOrderInput | SortOrder
    image?: SortOrderInput | SortOrder
    role?: SortOrder
    subscriptionStatus?: SortOrderInput | SortOrder
    subscriptionPlan?: SortOrderInput | SortOrder
    subscriptionStart?: SortOrderInput | SortOrder
    subscriptionEnd?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    _count?: UserCountOrderByAggregateInput
    _max?: UserMaxOrderByAggregateInput
    _min?: UserMinOrderByAggregateInput
  }

  export type UserScalarWhereWithAggregatesInput = {
    AND?: UserScalarWhereWithAggregatesInput | UserScalarWhereWithAggregatesInput[]
    OR?: UserScalarWhereWithAggregatesInput[]
    NOT?: UserScalarWhereWithAggregatesInput | UserScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"User"> | string
    email?: StringWithAggregatesFilter<"User"> | string
    emailVerified?: DateTimeNullableWithAggregatesFilter<"User"> | Date | string | null
    name?: StringNullableWithAggregatesFilter<"User"> | string | null
    password?: StringNullableWithAggregatesFilter<"User"> | string | null
    image?: StringNullableWithAggregatesFilter<"User"> | string | null
    role?: EnumUserRoleWithAggregatesFilter<"User"> | $Enums.UserRole
    subscriptionStatus?: EnumSubscriptionStatusNullableWithAggregatesFilter<"User"> | $Enums.SubscriptionStatus | null
    subscriptionPlan?: StringNullableWithAggregatesFilter<"User"> | string | null
    subscriptionStart?: DateTimeNullableWithAggregatesFilter<"User"> | Date | string | null
    subscriptionEnd?: DateTimeNullableWithAggregatesFilter<"User"> | Date | string | null
    createdAt?: DateTimeWithAggregatesFilter<"User"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"User"> | Date | string
  }

  export type AccountWhereInput = {
    AND?: AccountWhereInput | AccountWhereInput[]
    OR?: AccountWhereInput[]
    NOT?: AccountWhereInput | AccountWhereInput[]
    id?: StringFilter<"Account"> | string
    userId?: StringFilter<"Account"> | string
    type?: StringFilter<"Account"> | string
    provider?: StringFilter<"Account"> | string
    providerAccountId?: StringFilter<"Account"> | string
    refresh_token?: StringNullableFilter<"Account"> | string | null
    access_token?: StringNullableFilter<"Account"> | string | null
    expires_at?: IntNullableFilter<"Account"> | number | null
    token_type?: StringNullableFilter<"Account"> | string | null
    scope?: StringNullableFilter<"Account"> | string | null
    id_token?: StringNullableFilter<"Account"> | string | null
    session_state?: StringNullableFilter<"Account"> | string | null
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }

  export type AccountOrderByWithRelationInput = {
    id?: SortOrder
    userId?: SortOrder
    type?: SortOrder
    provider?: SortOrder
    providerAccountId?: SortOrder
    refresh_token?: SortOrderInput | SortOrder
    access_token?: SortOrderInput | SortOrder
    expires_at?: SortOrderInput | SortOrder
    token_type?: SortOrderInput | SortOrder
    scope?: SortOrderInput | SortOrder
    id_token?: SortOrderInput | SortOrder
    session_state?: SortOrderInput | SortOrder
    user?: UserOrderByWithRelationInput
  }

  export type AccountWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    provider_providerAccountId?: AccountProviderProviderAccountIdCompoundUniqueInput
    AND?: AccountWhereInput | AccountWhereInput[]
    OR?: AccountWhereInput[]
    NOT?: AccountWhereInput | AccountWhereInput[]
    userId?: StringFilter<"Account"> | string
    type?: StringFilter<"Account"> | string
    provider?: StringFilter<"Account"> | string
    providerAccountId?: StringFilter<"Account"> | string
    refresh_token?: StringNullableFilter<"Account"> | string | null
    access_token?: StringNullableFilter<"Account"> | string | null
    expires_at?: IntNullableFilter<"Account"> | number | null
    token_type?: StringNullableFilter<"Account"> | string | null
    scope?: StringNullableFilter<"Account"> | string | null
    id_token?: StringNullableFilter<"Account"> | string | null
    session_state?: StringNullableFilter<"Account"> | string | null
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }, "id" | "provider_providerAccountId">

  export type AccountOrderByWithAggregationInput = {
    id?: SortOrder
    userId?: SortOrder
    type?: SortOrder
    provider?: SortOrder
    providerAccountId?: SortOrder
    refresh_token?: SortOrderInput | SortOrder
    access_token?: SortOrderInput | SortOrder
    expires_at?: SortOrderInput | SortOrder
    token_type?: SortOrderInput | SortOrder
    scope?: SortOrderInput | SortOrder
    id_token?: SortOrderInput | SortOrder
    session_state?: SortOrderInput | SortOrder
    _count?: AccountCountOrderByAggregateInput
    _avg?: AccountAvgOrderByAggregateInput
    _max?: AccountMaxOrderByAggregateInput
    _min?: AccountMinOrderByAggregateInput
    _sum?: AccountSumOrderByAggregateInput
  }

  export type AccountScalarWhereWithAggregatesInput = {
    AND?: AccountScalarWhereWithAggregatesInput | AccountScalarWhereWithAggregatesInput[]
    OR?: AccountScalarWhereWithAggregatesInput[]
    NOT?: AccountScalarWhereWithAggregatesInput | AccountScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Account"> | string
    userId?: StringWithAggregatesFilter<"Account"> | string
    type?: StringWithAggregatesFilter<"Account"> | string
    provider?: StringWithAggregatesFilter<"Account"> | string
    providerAccountId?: StringWithAggregatesFilter<"Account"> | string
    refresh_token?: StringNullableWithAggregatesFilter<"Account"> | string | null
    access_token?: StringNullableWithAggregatesFilter<"Account"> | string | null
    expires_at?: IntNullableWithAggregatesFilter<"Account"> | number | null
    token_type?: StringNullableWithAggregatesFilter<"Account"> | string | null
    scope?: StringNullableWithAggregatesFilter<"Account"> | string | null
    id_token?: StringNullableWithAggregatesFilter<"Account"> | string | null
    session_state?: StringNullableWithAggregatesFilter<"Account"> | string | null
  }

  export type SessionWhereInput = {
    AND?: SessionWhereInput | SessionWhereInput[]
    OR?: SessionWhereInput[]
    NOT?: SessionWhereInput | SessionWhereInput[]
    id?: StringFilter<"Session"> | string
    sessionToken?: StringFilter<"Session"> | string
    userId?: StringFilter<"Session"> | string
    expires?: DateTimeFilter<"Session"> | Date | string
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }

  export type SessionOrderByWithRelationInput = {
    id?: SortOrder
    sessionToken?: SortOrder
    userId?: SortOrder
    expires?: SortOrder
    user?: UserOrderByWithRelationInput
  }

  export type SessionWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    sessionToken?: string
    AND?: SessionWhereInput | SessionWhereInput[]
    OR?: SessionWhereInput[]
    NOT?: SessionWhereInput | SessionWhereInput[]
    userId?: StringFilter<"Session"> | string
    expires?: DateTimeFilter<"Session"> | Date | string
    user?: XOR<UserScalarRelationFilter, UserWhereInput>
  }, "id" | "sessionToken">

  export type SessionOrderByWithAggregationInput = {
    id?: SortOrder
    sessionToken?: SortOrder
    userId?: SortOrder
    expires?: SortOrder
    _count?: SessionCountOrderByAggregateInput
    _max?: SessionMaxOrderByAggregateInput
    _min?: SessionMinOrderByAggregateInput
  }

  export type SessionScalarWhereWithAggregatesInput = {
    AND?: SessionScalarWhereWithAggregatesInput | SessionScalarWhereWithAggregatesInput[]
    OR?: SessionScalarWhereWithAggregatesInput[]
    NOT?: SessionScalarWhereWithAggregatesInput | SessionScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Session"> | string
    sessionToken?: StringWithAggregatesFilter<"Session"> | string
    userId?: StringWithAggregatesFilter<"Session"> | string
    expires?: DateTimeWithAggregatesFilter<"Session"> | Date | string
  }

  export type VerificationTokenWhereInput = {
    AND?: VerificationTokenWhereInput | VerificationTokenWhereInput[]
    OR?: VerificationTokenWhereInput[]
    NOT?: VerificationTokenWhereInput | VerificationTokenWhereInput[]
    identifier?: StringFilter<"VerificationToken"> | string
    token?: StringFilter<"VerificationToken"> | string
    expires?: DateTimeFilter<"VerificationToken"> | Date | string
  }

  export type VerificationTokenOrderByWithRelationInput = {
    identifier?: SortOrder
    token?: SortOrder
    expires?: SortOrder
  }

  export type VerificationTokenWhereUniqueInput = Prisma.AtLeast<{
    token?: string
    identifier_token?: VerificationTokenIdentifierTokenCompoundUniqueInput
    AND?: VerificationTokenWhereInput | VerificationTokenWhereInput[]
    OR?: VerificationTokenWhereInput[]
    NOT?: VerificationTokenWhereInput | VerificationTokenWhereInput[]
    identifier?: StringFilter<"VerificationToken"> | string
    expires?: DateTimeFilter<"VerificationToken"> | Date | string
  }, "token" | "identifier_token">

  export type VerificationTokenOrderByWithAggregationInput = {
    identifier?: SortOrder
    token?: SortOrder
    expires?: SortOrder
    _count?: VerificationTokenCountOrderByAggregateInput
    _max?: VerificationTokenMaxOrderByAggregateInput
    _min?: VerificationTokenMinOrderByAggregateInput
  }

  export type VerificationTokenScalarWhereWithAggregatesInput = {
    AND?: VerificationTokenScalarWhereWithAggregatesInput | VerificationTokenScalarWhereWithAggregatesInput[]
    OR?: VerificationTokenScalarWhereWithAggregatesInput[]
    NOT?: VerificationTokenScalarWhereWithAggregatesInput | VerificationTokenScalarWhereWithAggregatesInput[]
    identifier?: StringWithAggregatesFilter<"VerificationToken"> | string
    token?: StringWithAggregatesFilter<"VerificationToken"> | string
    expires?: DateTimeWithAggregatesFilter<"VerificationToken"> | Date | string
  }

  export type SportWhereInput = {
    AND?: SportWhereInput | SportWhereInput[]
    OR?: SportWhereInput[]
    NOT?: SportWhereInput | SportWhereInput[]
    id?: StringFilter<"Sport"> | string
    key?: StringFilter<"Sport"> | string
    name?: StringFilter<"Sport"> | string
    createdAt?: DateTimeFilter<"Sport"> | Date | string
    updatedAt?: DateTimeFilter<"Sport"> | Date | string
    teams?: TeamListRelationFilter
    games?: GameListRelationFilter
  }

  export type SportOrderByWithRelationInput = {
    id?: SortOrder
    key?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    teams?: TeamOrderByRelationAggregateInput
    games?: GameOrderByRelationAggregateInput
  }

  export type SportWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    key?: string
    AND?: SportWhereInput | SportWhereInput[]
    OR?: SportWhereInput[]
    NOT?: SportWhereInput | SportWhereInput[]
    name?: StringFilter<"Sport"> | string
    createdAt?: DateTimeFilter<"Sport"> | Date | string
    updatedAt?: DateTimeFilter<"Sport"> | Date | string
    teams?: TeamListRelationFilter
    games?: GameListRelationFilter
  }, "id" | "key">

  export type SportOrderByWithAggregationInput = {
    id?: SortOrder
    key?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    _count?: SportCountOrderByAggregateInput
    _max?: SportMaxOrderByAggregateInput
    _min?: SportMinOrderByAggregateInput
  }

  export type SportScalarWhereWithAggregatesInput = {
    AND?: SportScalarWhereWithAggregatesInput | SportScalarWhereWithAggregatesInput[]
    OR?: SportScalarWhereWithAggregatesInput[]
    NOT?: SportScalarWhereWithAggregatesInput | SportScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Sport"> | string
    key?: StringWithAggregatesFilter<"Sport"> | string
    name?: StringWithAggregatesFilter<"Sport"> | string
    createdAt?: DateTimeWithAggregatesFilter<"Sport"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"Sport"> | Date | string
  }

  export type TeamWhereInput = {
    AND?: TeamWhereInput | TeamWhereInput[]
    OR?: TeamWhereInput[]
    NOT?: TeamWhereInput | TeamWhereInput[]
    id?: StringFilter<"Team"> | string
    sportId?: StringFilter<"Team"> | string
    name?: StringFilter<"Team"> | string
    slug?: StringFilter<"Team"> | string
    abbr?: StringNullableFilter<"Team"> | string | null
    createdAt?: DateTimeFilter<"Team"> | Date | string
    updatedAt?: DateTimeFilter<"Team"> | Date | string
    sport?: XOR<SportScalarRelationFilter, SportWhereInput>
    homeGames?: GameListRelationFilter
    awayGames?: GameListRelationFilter
    injuries?: InjuryListRelationFilter
    profiles?: TeamProfileWeeklyListRelationFilter
  }

  export type TeamOrderByWithRelationInput = {
    id?: SortOrder
    sportId?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    abbr?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    sport?: SportOrderByWithRelationInput
    homeGames?: GameOrderByRelationAggregateInput
    awayGames?: GameOrderByRelationAggregateInput
    injuries?: InjuryOrderByRelationAggregateInput
    profiles?: TeamProfileWeeklyOrderByRelationAggregateInput
  }

  export type TeamWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    sportId_slug?: TeamSportIdSlugCompoundUniqueInput
    AND?: TeamWhereInput | TeamWhereInput[]
    OR?: TeamWhereInput[]
    NOT?: TeamWhereInput | TeamWhereInput[]
    sportId?: StringFilter<"Team"> | string
    name?: StringFilter<"Team"> | string
    slug?: StringFilter<"Team"> | string
    abbr?: StringNullableFilter<"Team"> | string | null
    createdAt?: DateTimeFilter<"Team"> | Date | string
    updatedAt?: DateTimeFilter<"Team"> | Date | string
    sport?: XOR<SportScalarRelationFilter, SportWhereInput>
    homeGames?: GameListRelationFilter
    awayGames?: GameListRelationFilter
    injuries?: InjuryListRelationFilter
    profiles?: TeamProfileWeeklyListRelationFilter
  }, "id" | "sportId_slug">

  export type TeamOrderByWithAggregationInput = {
    id?: SortOrder
    sportId?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    abbr?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    _count?: TeamCountOrderByAggregateInput
    _max?: TeamMaxOrderByAggregateInput
    _min?: TeamMinOrderByAggregateInput
  }

  export type TeamScalarWhereWithAggregatesInput = {
    AND?: TeamScalarWhereWithAggregatesInput | TeamScalarWhereWithAggregatesInput[]
    OR?: TeamScalarWhereWithAggregatesInput[]
    NOT?: TeamScalarWhereWithAggregatesInput | TeamScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Team"> | string
    sportId?: StringWithAggregatesFilter<"Team"> | string
    name?: StringWithAggregatesFilter<"Team"> | string
    slug?: StringWithAggregatesFilter<"Team"> | string
    abbr?: StringNullableWithAggregatesFilter<"Team"> | string | null
    createdAt?: DateTimeWithAggregatesFilter<"Team"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"Team"> | Date | string
  }

  export type GameWhereInput = {
    AND?: GameWhereInput | GameWhereInput[]
    OR?: GameWhereInput[]
    NOT?: GameWhereInput | GameWhereInput[]
    id?: StringFilter<"Game"> | string
    sportId?: StringFilter<"Game"> | string
    date?: DateTimeFilter<"Game"> | Date | string
    slug?: StringFilter<"Game"> | string
    homeTeamId?: StringFilter<"Game"> | string
    awayTeamId?: StringFilter<"Game"> | string
    startTime?: DateTimeNullableFilter<"Game"> | Date | string | null
    venue?: StringNullableFilter<"Game"> | string | null
    createdAt?: DateTimeFilter<"Game"> | Date | string
    updatedAt?: DateTimeFilter<"Game"> | Date | string
    sport?: XOR<SportScalarRelationFilter, SportWhereInput>
    homeTeam?: XOR<TeamScalarRelationFilter, TeamWhereInput>
    awayTeam?: XOR<TeamScalarRelationFilter, TeamWhereInput>
    market?: XOR<MarketSnapshotNullableScalarRelationFilter, MarketSnapshotWhereInput> | null
    model?: XOR<ModelProjectionNullableScalarRelationFilter, ModelProjectionWhereInput> | null
    writeup?: XOR<WriteupNullableScalarRelationFilter, WriteupWhereInput> | null
  }

  export type GameOrderByWithRelationInput = {
    id?: SortOrder
    sportId?: SortOrder
    date?: SortOrder
    slug?: SortOrder
    homeTeamId?: SortOrder
    awayTeamId?: SortOrder
    startTime?: SortOrderInput | SortOrder
    venue?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    sport?: SportOrderByWithRelationInput
    homeTeam?: TeamOrderByWithRelationInput
    awayTeam?: TeamOrderByWithRelationInput
    market?: MarketSnapshotOrderByWithRelationInput
    model?: ModelProjectionOrderByWithRelationInput
    writeup?: WriteupOrderByWithRelationInput
  }

  export type GameWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    sportId_date_slug?: GameSportIdDateSlugCompoundUniqueInput
    AND?: GameWhereInput | GameWhereInput[]
    OR?: GameWhereInput[]
    NOT?: GameWhereInput | GameWhereInput[]
    sportId?: StringFilter<"Game"> | string
    date?: DateTimeFilter<"Game"> | Date | string
    slug?: StringFilter<"Game"> | string
    homeTeamId?: StringFilter<"Game"> | string
    awayTeamId?: StringFilter<"Game"> | string
    startTime?: DateTimeNullableFilter<"Game"> | Date | string | null
    venue?: StringNullableFilter<"Game"> | string | null
    createdAt?: DateTimeFilter<"Game"> | Date | string
    updatedAt?: DateTimeFilter<"Game"> | Date | string
    sport?: XOR<SportScalarRelationFilter, SportWhereInput>
    homeTeam?: XOR<TeamScalarRelationFilter, TeamWhereInput>
    awayTeam?: XOR<TeamScalarRelationFilter, TeamWhereInput>
    market?: XOR<MarketSnapshotNullableScalarRelationFilter, MarketSnapshotWhereInput> | null
    model?: XOR<ModelProjectionNullableScalarRelationFilter, ModelProjectionWhereInput> | null
    writeup?: XOR<WriteupNullableScalarRelationFilter, WriteupWhereInput> | null
  }, "id" | "sportId_date_slug">

  export type GameOrderByWithAggregationInput = {
    id?: SortOrder
    sportId?: SortOrder
    date?: SortOrder
    slug?: SortOrder
    homeTeamId?: SortOrder
    awayTeamId?: SortOrder
    startTime?: SortOrderInput | SortOrder
    venue?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    _count?: GameCountOrderByAggregateInput
    _max?: GameMaxOrderByAggregateInput
    _min?: GameMinOrderByAggregateInput
  }

  export type GameScalarWhereWithAggregatesInput = {
    AND?: GameScalarWhereWithAggregatesInput | GameScalarWhereWithAggregatesInput[]
    OR?: GameScalarWhereWithAggregatesInput[]
    NOT?: GameScalarWhereWithAggregatesInput | GameScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Game"> | string
    sportId?: StringWithAggregatesFilter<"Game"> | string
    date?: DateTimeWithAggregatesFilter<"Game"> | Date | string
    slug?: StringWithAggregatesFilter<"Game"> | string
    homeTeamId?: StringWithAggregatesFilter<"Game"> | string
    awayTeamId?: StringWithAggregatesFilter<"Game"> | string
    startTime?: DateTimeNullableWithAggregatesFilter<"Game"> | Date | string | null
    venue?: StringNullableWithAggregatesFilter<"Game"> | string | null
    createdAt?: DateTimeWithAggregatesFilter<"Game"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"Game"> | Date | string
  }

  export type MarketSnapshotWhereInput = {
    AND?: MarketSnapshotWhereInput | MarketSnapshotWhereInput[]
    OR?: MarketSnapshotWhereInput[]
    NOT?: MarketSnapshotWhereInput | MarketSnapshotWhereInput[]
    id?: StringFilter<"MarketSnapshot"> | string
    gameId?: StringFilter<"MarketSnapshot"> | string
    capturedAt?: DateTimeFilter<"MarketSnapshot"> | Date | string
    openSpreadHome?: FloatNullableFilter<"MarketSnapshot"> | number | null
    currentSpreadHome?: FloatNullableFilter<"MarketSnapshot"> | number | null
    openTotal?: FloatNullableFilter<"MarketSnapshot"> | number | null
    currentTotal?: FloatNullableFilter<"MarketSnapshot"> | number | null
    bestSpreadHome?: FloatNullableFilter<"MarketSnapshot"> | number | null
    bestSpreadBook?: StringNullableFilter<"MarketSnapshot"> | string | null
    bestTotal?: FloatNullableFilter<"MarketSnapshot"> | number | null
    bestTotalBook?: StringNullableFilter<"MarketSnapshot"> | string | null
    spreadDispersion?: FloatNullableFilter<"MarketSnapshot"> | number | null
    totalDispersion?: FloatNullableFilter<"MarketSnapshot"> | number | null
    bookLines?: BookLineListRelationFilter
    game?: XOR<GameScalarRelationFilter, GameWhereInput>
  }

  export type MarketSnapshotOrderByWithRelationInput = {
    id?: SortOrder
    gameId?: SortOrder
    capturedAt?: SortOrder
    openSpreadHome?: SortOrderInput | SortOrder
    currentSpreadHome?: SortOrderInput | SortOrder
    openTotal?: SortOrderInput | SortOrder
    currentTotal?: SortOrderInput | SortOrder
    bestSpreadHome?: SortOrderInput | SortOrder
    bestSpreadBook?: SortOrderInput | SortOrder
    bestTotal?: SortOrderInput | SortOrder
    bestTotalBook?: SortOrderInput | SortOrder
    spreadDispersion?: SortOrderInput | SortOrder
    totalDispersion?: SortOrderInput | SortOrder
    bookLines?: BookLineOrderByRelationAggregateInput
    game?: GameOrderByWithRelationInput
  }

  export type MarketSnapshotWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    gameId?: string
    AND?: MarketSnapshotWhereInput | MarketSnapshotWhereInput[]
    OR?: MarketSnapshotWhereInput[]
    NOT?: MarketSnapshotWhereInput | MarketSnapshotWhereInput[]
    capturedAt?: DateTimeFilter<"MarketSnapshot"> | Date | string
    openSpreadHome?: FloatNullableFilter<"MarketSnapshot"> | number | null
    currentSpreadHome?: FloatNullableFilter<"MarketSnapshot"> | number | null
    openTotal?: FloatNullableFilter<"MarketSnapshot"> | number | null
    currentTotal?: FloatNullableFilter<"MarketSnapshot"> | number | null
    bestSpreadHome?: FloatNullableFilter<"MarketSnapshot"> | number | null
    bestSpreadBook?: StringNullableFilter<"MarketSnapshot"> | string | null
    bestTotal?: FloatNullableFilter<"MarketSnapshot"> | number | null
    bestTotalBook?: StringNullableFilter<"MarketSnapshot"> | string | null
    spreadDispersion?: FloatNullableFilter<"MarketSnapshot"> | number | null
    totalDispersion?: FloatNullableFilter<"MarketSnapshot"> | number | null
    bookLines?: BookLineListRelationFilter
    game?: XOR<GameScalarRelationFilter, GameWhereInput>
  }, "id" | "gameId">

  export type MarketSnapshotOrderByWithAggregationInput = {
    id?: SortOrder
    gameId?: SortOrder
    capturedAt?: SortOrder
    openSpreadHome?: SortOrderInput | SortOrder
    currentSpreadHome?: SortOrderInput | SortOrder
    openTotal?: SortOrderInput | SortOrder
    currentTotal?: SortOrderInput | SortOrder
    bestSpreadHome?: SortOrderInput | SortOrder
    bestSpreadBook?: SortOrderInput | SortOrder
    bestTotal?: SortOrderInput | SortOrder
    bestTotalBook?: SortOrderInput | SortOrder
    spreadDispersion?: SortOrderInput | SortOrder
    totalDispersion?: SortOrderInput | SortOrder
    _count?: MarketSnapshotCountOrderByAggregateInput
    _avg?: MarketSnapshotAvgOrderByAggregateInput
    _max?: MarketSnapshotMaxOrderByAggregateInput
    _min?: MarketSnapshotMinOrderByAggregateInput
    _sum?: MarketSnapshotSumOrderByAggregateInput
  }

  export type MarketSnapshotScalarWhereWithAggregatesInput = {
    AND?: MarketSnapshotScalarWhereWithAggregatesInput | MarketSnapshotScalarWhereWithAggregatesInput[]
    OR?: MarketSnapshotScalarWhereWithAggregatesInput[]
    NOT?: MarketSnapshotScalarWhereWithAggregatesInput | MarketSnapshotScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"MarketSnapshot"> | string
    gameId?: StringWithAggregatesFilter<"MarketSnapshot"> | string
    capturedAt?: DateTimeWithAggregatesFilter<"MarketSnapshot"> | Date | string
    openSpreadHome?: FloatNullableWithAggregatesFilter<"MarketSnapshot"> | number | null
    currentSpreadHome?: FloatNullableWithAggregatesFilter<"MarketSnapshot"> | number | null
    openTotal?: FloatNullableWithAggregatesFilter<"MarketSnapshot"> | number | null
    currentTotal?: FloatNullableWithAggregatesFilter<"MarketSnapshot"> | number | null
    bestSpreadHome?: FloatNullableWithAggregatesFilter<"MarketSnapshot"> | number | null
    bestSpreadBook?: StringNullableWithAggregatesFilter<"MarketSnapshot"> | string | null
    bestTotal?: FloatNullableWithAggregatesFilter<"MarketSnapshot"> | number | null
    bestTotalBook?: StringNullableWithAggregatesFilter<"MarketSnapshot"> | string | null
    spreadDispersion?: FloatNullableWithAggregatesFilter<"MarketSnapshot"> | number | null
    totalDispersion?: FloatNullableWithAggregatesFilter<"MarketSnapshot"> | number | null
  }

  export type BookLineWhereInput = {
    AND?: BookLineWhereInput | BookLineWhereInput[]
    OR?: BookLineWhereInput[]
    NOT?: BookLineWhereInput | BookLineWhereInput[]
    id?: StringFilter<"BookLine"> | string
    marketId?: StringFilter<"BookLine"> | string
    book?: StringFilter<"BookLine"> | string
    capturedAt?: DateTimeFilter<"BookLine"> | Date | string
    spreadHome?: FloatNullableFilter<"BookLine"> | number | null
    spreadAway?: FloatNullableFilter<"BookLine"> | number | null
    total?: FloatNullableFilter<"BookLine"> | number | null
    market?: XOR<MarketSnapshotScalarRelationFilter, MarketSnapshotWhereInput>
  }

  export type BookLineOrderByWithRelationInput = {
    id?: SortOrder
    marketId?: SortOrder
    book?: SortOrder
    capturedAt?: SortOrder
    spreadHome?: SortOrderInput | SortOrder
    spreadAway?: SortOrderInput | SortOrder
    total?: SortOrderInput | SortOrder
    market?: MarketSnapshotOrderByWithRelationInput
  }

  export type BookLineWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: BookLineWhereInput | BookLineWhereInput[]
    OR?: BookLineWhereInput[]
    NOT?: BookLineWhereInput | BookLineWhereInput[]
    marketId?: StringFilter<"BookLine"> | string
    book?: StringFilter<"BookLine"> | string
    capturedAt?: DateTimeFilter<"BookLine"> | Date | string
    spreadHome?: FloatNullableFilter<"BookLine"> | number | null
    spreadAway?: FloatNullableFilter<"BookLine"> | number | null
    total?: FloatNullableFilter<"BookLine"> | number | null
    market?: XOR<MarketSnapshotScalarRelationFilter, MarketSnapshotWhereInput>
  }, "id">

  export type BookLineOrderByWithAggregationInput = {
    id?: SortOrder
    marketId?: SortOrder
    book?: SortOrder
    capturedAt?: SortOrder
    spreadHome?: SortOrderInput | SortOrder
    spreadAway?: SortOrderInput | SortOrder
    total?: SortOrderInput | SortOrder
    _count?: BookLineCountOrderByAggregateInput
    _avg?: BookLineAvgOrderByAggregateInput
    _max?: BookLineMaxOrderByAggregateInput
    _min?: BookLineMinOrderByAggregateInput
    _sum?: BookLineSumOrderByAggregateInput
  }

  export type BookLineScalarWhereWithAggregatesInput = {
    AND?: BookLineScalarWhereWithAggregatesInput | BookLineScalarWhereWithAggregatesInput[]
    OR?: BookLineScalarWhereWithAggregatesInput[]
    NOT?: BookLineScalarWhereWithAggregatesInput | BookLineScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"BookLine"> | string
    marketId?: StringWithAggregatesFilter<"BookLine"> | string
    book?: StringWithAggregatesFilter<"BookLine"> | string
    capturedAt?: DateTimeWithAggregatesFilter<"BookLine"> | Date | string
    spreadHome?: FloatNullableWithAggregatesFilter<"BookLine"> | number | null
    spreadAway?: FloatNullableWithAggregatesFilter<"BookLine"> | number | null
    total?: FloatNullableWithAggregatesFilter<"BookLine"> | number | null
  }

  export type ModelProjectionWhereInput = {
    AND?: ModelProjectionWhereInput | ModelProjectionWhereInput[]
    OR?: ModelProjectionWhereInput[]
    NOT?: ModelProjectionWhereInput | ModelProjectionWhereInput[]
    id?: StringFilter<"ModelProjection"> | string
    gameId?: StringFilter<"ModelProjection"> | string
    version?: StringFilter<"ModelProjection"> | string
    computedAt?: DateTimeFilter<"ModelProjection"> | Date | string
    projSpreadHome?: FloatFilter<"ModelProjection"> | number
    projTotal?: FloatFilter<"ModelProjection"> | number
    game?: XOR<GameScalarRelationFilter, GameWhereInput>
  }

  export type ModelProjectionOrderByWithRelationInput = {
    id?: SortOrder
    gameId?: SortOrder
    version?: SortOrder
    computedAt?: SortOrder
    projSpreadHome?: SortOrder
    projTotal?: SortOrder
    game?: GameOrderByWithRelationInput
  }

  export type ModelProjectionWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    gameId?: string
    AND?: ModelProjectionWhereInput | ModelProjectionWhereInput[]
    OR?: ModelProjectionWhereInput[]
    NOT?: ModelProjectionWhereInput | ModelProjectionWhereInput[]
    version?: StringFilter<"ModelProjection"> | string
    computedAt?: DateTimeFilter<"ModelProjection"> | Date | string
    projSpreadHome?: FloatFilter<"ModelProjection"> | number
    projTotal?: FloatFilter<"ModelProjection"> | number
    game?: XOR<GameScalarRelationFilter, GameWhereInput>
  }, "id" | "gameId">

  export type ModelProjectionOrderByWithAggregationInput = {
    id?: SortOrder
    gameId?: SortOrder
    version?: SortOrder
    computedAt?: SortOrder
    projSpreadHome?: SortOrder
    projTotal?: SortOrder
    _count?: ModelProjectionCountOrderByAggregateInput
    _avg?: ModelProjectionAvgOrderByAggregateInput
    _max?: ModelProjectionMaxOrderByAggregateInput
    _min?: ModelProjectionMinOrderByAggregateInput
    _sum?: ModelProjectionSumOrderByAggregateInput
  }

  export type ModelProjectionScalarWhereWithAggregatesInput = {
    AND?: ModelProjectionScalarWhereWithAggregatesInput | ModelProjectionScalarWhereWithAggregatesInput[]
    OR?: ModelProjectionScalarWhereWithAggregatesInput[]
    NOT?: ModelProjectionScalarWhereWithAggregatesInput | ModelProjectionScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"ModelProjection"> | string
    gameId?: StringWithAggregatesFilter<"ModelProjection"> | string
    version?: StringWithAggregatesFilter<"ModelProjection"> | string
    computedAt?: DateTimeWithAggregatesFilter<"ModelProjection"> | Date | string
    projSpreadHome?: FloatWithAggregatesFilter<"ModelProjection"> | number
    projTotal?: FloatWithAggregatesFilter<"ModelProjection"> | number
  }

  export type WriteupWhereInput = {
    AND?: WriteupWhereInput | WriteupWhereInput[]
    OR?: WriteupWhereInput[]
    NOT?: WriteupWhereInput | WriteupWhereInput[]
    id?: StringFilter<"Writeup"> | string
    gameId?: StringFilter<"Writeup"> | string
    createdAt?: DateTimeFilter<"Writeup"> | Date | string
    updatedAt?: DateTimeFilter<"Writeup"> | Date | string
    formatKey?: StringFilter<"Writeup"> | string
    body?: StringFilter<"Writeup"> | string
    disclosedAi?: BoolFilter<"Writeup"> | boolean
    editorStatus?: EnumEditorStatusFilter<"Writeup"> | $Enums.EditorStatus
    game?: XOR<GameScalarRelationFilter, GameWhereInput>
  }

  export type WriteupOrderByWithRelationInput = {
    id?: SortOrder
    gameId?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    formatKey?: SortOrder
    body?: SortOrder
    disclosedAi?: SortOrder
    editorStatus?: SortOrder
    game?: GameOrderByWithRelationInput
  }

  export type WriteupWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    gameId?: string
    AND?: WriteupWhereInput | WriteupWhereInput[]
    OR?: WriteupWhereInput[]
    NOT?: WriteupWhereInput | WriteupWhereInput[]
    createdAt?: DateTimeFilter<"Writeup"> | Date | string
    updatedAt?: DateTimeFilter<"Writeup"> | Date | string
    formatKey?: StringFilter<"Writeup"> | string
    body?: StringFilter<"Writeup"> | string
    disclosedAi?: BoolFilter<"Writeup"> | boolean
    editorStatus?: EnumEditorStatusFilter<"Writeup"> | $Enums.EditorStatus
    game?: XOR<GameScalarRelationFilter, GameWhereInput>
  }, "id" | "gameId">

  export type WriteupOrderByWithAggregationInput = {
    id?: SortOrder
    gameId?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    formatKey?: SortOrder
    body?: SortOrder
    disclosedAi?: SortOrder
    editorStatus?: SortOrder
    _count?: WriteupCountOrderByAggregateInput
    _max?: WriteupMaxOrderByAggregateInput
    _min?: WriteupMinOrderByAggregateInput
  }

  export type WriteupScalarWhereWithAggregatesInput = {
    AND?: WriteupScalarWhereWithAggregatesInput | WriteupScalarWhereWithAggregatesInput[]
    OR?: WriteupScalarWhereWithAggregatesInput[]
    NOT?: WriteupScalarWhereWithAggregatesInput | WriteupScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Writeup"> | string
    gameId?: StringWithAggregatesFilter<"Writeup"> | string
    createdAt?: DateTimeWithAggregatesFilter<"Writeup"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"Writeup"> | Date | string
    formatKey?: StringWithAggregatesFilter<"Writeup"> | string
    body?: StringWithAggregatesFilter<"Writeup"> | string
    disclosedAi?: BoolWithAggregatesFilter<"Writeup"> | boolean
    editorStatus?: EnumEditorStatusWithAggregatesFilter<"Writeup"> | $Enums.EditorStatus
  }

  export type InjuryWhereInput = {
    AND?: InjuryWhereInput | InjuryWhereInput[]
    OR?: InjuryWhereInput[]
    NOT?: InjuryWhereInput | InjuryWhereInput[]
    id?: StringFilter<"Injury"> | string
    teamId?: StringFilter<"Injury"> | string
    date?: DateTimeFilter<"Injury"> | Date | string
    player?: StringFilter<"Injury"> | string
    status?: EnumInjuryStatusFilter<"Injury"> | $Enums.InjuryStatus
    note?: StringNullableFilter<"Injury"> | string | null
    impact?: EnumInjuryImpactNullableFilter<"Injury"> | $Enums.InjuryImpact | null
    createdAt?: DateTimeFilter<"Injury"> | Date | string
    updatedAt?: DateTimeFilter<"Injury"> | Date | string
    team?: XOR<TeamScalarRelationFilter, TeamWhereInput>
  }

  export type InjuryOrderByWithRelationInput = {
    id?: SortOrder
    teamId?: SortOrder
    date?: SortOrder
    player?: SortOrder
    status?: SortOrder
    note?: SortOrderInput | SortOrder
    impact?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    team?: TeamOrderByWithRelationInput
  }

  export type InjuryWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: InjuryWhereInput | InjuryWhereInput[]
    OR?: InjuryWhereInput[]
    NOT?: InjuryWhereInput | InjuryWhereInput[]
    teamId?: StringFilter<"Injury"> | string
    date?: DateTimeFilter<"Injury"> | Date | string
    player?: StringFilter<"Injury"> | string
    status?: EnumInjuryStatusFilter<"Injury"> | $Enums.InjuryStatus
    note?: StringNullableFilter<"Injury"> | string | null
    impact?: EnumInjuryImpactNullableFilter<"Injury"> | $Enums.InjuryImpact | null
    createdAt?: DateTimeFilter<"Injury"> | Date | string
    updatedAt?: DateTimeFilter<"Injury"> | Date | string
    team?: XOR<TeamScalarRelationFilter, TeamWhereInput>
  }, "id">

  export type InjuryOrderByWithAggregationInput = {
    id?: SortOrder
    teamId?: SortOrder
    date?: SortOrder
    player?: SortOrder
    status?: SortOrder
    note?: SortOrderInput | SortOrder
    impact?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    _count?: InjuryCountOrderByAggregateInput
    _max?: InjuryMaxOrderByAggregateInput
    _min?: InjuryMinOrderByAggregateInput
  }

  export type InjuryScalarWhereWithAggregatesInput = {
    AND?: InjuryScalarWhereWithAggregatesInput | InjuryScalarWhereWithAggregatesInput[]
    OR?: InjuryScalarWhereWithAggregatesInput[]
    NOT?: InjuryScalarWhereWithAggregatesInput | InjuryScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Injury"> | string
    teamId?: StringWithAggregatesFilter<"Injury"> | string
    date?: DateTimeWithAggregatesFilter<"Injury"> | Date | string
    player?: StringWithAggregatesFilter<"Injury"> | string
    status?: EnumInjuryStatusWithAggregatesFilter<"Injury"> | $Enums.InjuryStatus
    note?: StringNullableWithAggregatesFilter<"Injury"> | string | null
    impact?: EnumInjuryImpactNullableWithAggregatesFilter<"Injury"> | $Enums.InjuryImpact | null
    createdAt?: DateTimeWithAggregatesFilter<"Injury"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"Injury"> | Date | string
  }

  export type TeamProfileWeeklyWhereInput = {
    AND?: TeamProfileWeeklyWhereInput | TeamProfileWeeklyWhereInput[]
    OR?: TeamProfileWeeklyWhereInput[]
    NOT?: TeamProfileWeeklyWhereInput | TeamProfileWeeklyWhereInput[]
    id?: StringFilter<"TeamProfileWeekly"> | string
    teamId?: StringFilter<"TeamProfileWeekly"> | string
    weekStart?: DateTimeFilter<"TeamProfileWeekly"> | Date | string
    summary?: StringFilter<"TeamProfileWeekly"> | string
    tempoRank?: IntNullableFilter<"TeamProfileWeekly"> | number | null
    offPpp?: FloatNullableFilter<"TeamProfileWeekly"> | number | null
    defPpp?: FloatNullableFilter<"TeamProfileWeekly"> | number | null
    createdAt?: DateTimeFilter<"TeamProfileWeekly"> | Date | string
    updatedAt?: DateTimeFilter<"TeamProfileWeekly"> | Date | string
    team?: XOR<TeamScalarRelationFilter, TeamWhereInput>
  }

  export type TeamProfileWeeklyOrderByWithRelationInput = {
    id?: SortOrder
    teamId?: SortOrder
    weekStart?: SortOrder
    summary?: SortOrder
    tempoRank?: SortOrderInput | SortOrder
    offPpp?: SortOrderInput | SortOrder
    defPpp?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    team?: TeamOrderByWithRelationInput
  }

  export type TeamProfileWeeklyWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    teamId_weekStart?: TeamProfileWeeklyTeamIdWeekStartCompoundUniqueInput
    AND?: TeamProfileWeeklyWhereInput | TeamProfileWeeklyWhereInput[]
    OR?: TeamProfileWeeklyWhereInput[]
    NOT?: TeamProfileWeeklyWhereInput | TeamProfileWeeklyWhereInput[]
    teamId?: StringFilter<"TeamProfileWeekly"> | string
    weekStart?: DateTimeFilter<"TeamProfileWeekly"> | Date | string
    summary?: StringFilter<"TeamProfileWeekly"> | string
    tempoRank?: IntNullableFilter<"TeamProfileWeekly"> | number | null
    offPpp?: FloatNullableFilter<"TeamProfileWeekly"> | number | null
    defPpp?: FloatNullableFilter<"TeamProfileWeekly"> | number | null
    createdAt?: DateTimeFilter<"TeamProfileWeekly"> | Date | string
    updatedAt?: DateTimeFilter<"TeamProfileWeekly"> | Date | string
    team?: XOR<TeamScalarRelationFilter, TeamWhereInput>
  }, "id" | "teamId_weekStart">

  export type TeamProfileWeeklyOrderByWithAggregationInput = {
    id?: SortOrder
    teamId?: SortOrder
    weekStart?: SortOrder
    summary?: SortOrder
    tempoRank?: SortOrderInput | SortOrder
    offPpp?: SortOrderInput | SortOrder
    defPpp?: SortOrderInput | SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    _count?: TeamProfileWeeklyCountOrderByAggregateInput
    _avg?: TeamProfileWeeklyAvgOrderByAggregateInput
    _max?: TeamProfileWeeklyMaxOrderByAggregateInput
    _min?: TeamProfileWeeklyMinOrderByAggregateInput
    _sum?: TeamProfileWeeklySumOrderByAggregateInput
  }

  export type TeamProfileWeeklyScalarWhereWithAggregatesInput = {
    AND?: TeamProfileWeeklyScalarWhereWithAggregatesInput | TeamProfileWeeklyScalarWhereWithAggregatesInput[]
    OR?: TeamProfileWeeklyScalarWhereWithAggregatesInput[]
    NOT?: TeamProfileWeeklyScalarWhereWithAggregatesInput | TeamProfileWeeklyScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"TeamProfileWeekly"> | string
    teamId?: StringWithAggregatesFilter<"TeamProfileWeekly"> | string
    weekStart?: DateTimeWithAggregatesFilter<"TeamProfileWeekly"> | Date | string
    summary?: StringWithAggregatesFilter<"TeamProfileWeekly"> | string
    tempoRank?: IntNullableWithAggregatesFilter<"TeamProfileWeekly"> | number | null
    offPpp?: FloatNullableWithAggregatesFilter<"TeamProfileWeekly"> | number | null
    defPpp?: FloatNullableWithAggregatesFilter<"TeamProfileWeekly"> | number | null
    createdAt?: DateTimeWithAggregatesFilter<"TeamProfileWeekly"> | Date | string
    updatedAt?: DateTimeWithAggregatesFilter<"TeamProfileWeekly"> | Date | string
  }

  export type UserCreateInput = {
    id?: string
    email: string
    emailVerified?: Date | string | null
    name?: string | null
    password?: string | null
    image?: string | null
    role?: $Enums.UserRole
    subscriptionStatus?: $Enums.SubscriptionStatus | null
    subscriptionPlan?: string | null
    subscriptionStart?: Date | string | null
    subscriptionEnd?: Date | string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    accounts?: AccountCreateNestedManyWithoutUserInput
    sessions?: SessionCreateNestedManyWithoutUserInput
  }

  export type UserUncheckedCreateInput = {
    id?: string
    email: string
    emailVerified?: Date | string | null
    name?: string | null
    password?: string | null
    image?: string | null
    role?: $Enums.UserRole
    subscriptionStatus?: $Enums.SubscriptionStatus | null
    subscriptionPlan?: string | null
    subscriptionStart?: Date | string | null
    subscriptionEnd?: Date | string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    accounts?: AccountUncheckedCreateNestedManyWithoutUserInput
    sessions?: SessionUncheckedCreateNestedManyWithoutUserInput
  }

  export type UserUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    emailVerified?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    name?: NullableStringFieldUpdateOperationsInput | string | null
    password?: NullableStringFieldUpdateOperationsInput | string | null
    image?: NullableStringFieldUpdateOperationsInput | string | null
    role?: EnumUserRoleFieldUpdateOperationsInput | $Enums.UserRole
    subscriptionStatus?: NullableEnumSubscriptionStatusFieldUpdateOperationsInput | $Enums.SubscriptionStatus | null
    subscriptionPlan?: NullableStringFieldUpdateOperationsInput | string | null
    subscriptionStart?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    subscriptionEnd?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    accounts?: AccountUpdateManyWithoutUserNestedInput
    sessions?: SessionUpdateManyWithoutUserNestedInput
  }

  export type UserUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    emailVerified?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    name?: NullableStringFieldUpdateOperationsInput | string | null
    password?: NullableStringFieldUpdateOperationsInput | string | null
    image?: NullableStringFieldUpdateOperationsInput | string | null
    role?: EnumUserRoleFieldUpdateOperationsInput | $Enums.UserRole
    subscriptionStatus?: NullableEnumSubscriptionStatusFieldUpdateOperationsInput | $Enums.SubscriptionStatus | null
    subscriptionPlan?: NullableStringFieldUpdateOperationsInput | string | null
    subscriptionStart?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    subscriptionEnd?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    accounts?: AccountUncheckedUpdateManyWithoutUserNestedInput
    sessions?: SessionUncheckedUpdateManyWithoutUserNestedInput
  }

  export type UserCreateManyInput = {
    id?: string
    email: string
    emailVerified?: Date | string | null
    name?: string | null
    password?: string | null
    image?: string | null
    role?: $Enums.UserRole
    subscriptionStatus?: $Enums.SubscriptionStatus | null
    subscriptionPlan?: string | null
    subscriptionStart?: Date | string | null
    subscriptionEnd?: Date | string | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type UserUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    emailVerified?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    name?: NullableStringFieldUpdateOperationsInput | string | null
    password?: NullableStringFieldUpdateOperationsInput | string | null
    image?: NullableStringFieldUpdateOperationsInput | string | null
    role?: EnumUserRoleFieldUpdateOperationsInput | $Enums.UserRole
    subscriptionStatus?: NullableEnumSubscriptionStatusFieldUpdateOperationsInput | $Enums.SubscriptionStatus | null
    subscriptionPlan?: NullableStringFieldUpdateOperationsInput | string | null
    subscriptionStart?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    subscriptionEnd?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type UserUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    emailVerified?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    name?: NullableStringFieldUpdateOperationsInput | string | null
    password?: NullableStringFieldUpdateOperationsInput | string | null
    image?: NullableStringFieldUpdateOperationsInput | string | null
    role?: EnumUserRoleFieldUpdateOperationsInput | $Enums.UserRole
    subscriptionStatus?: NullableEnumSubscriptionStatusFieldUpdateOperationsInput | $Enums.SubscriptionStatus | null
    subscriptionPlan?: NullableStringFieldUpdateOperationsInput | string | null
    subscriptionStart?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    subscriptionEnd?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type AccountCreateInput = {
    id?: string
    type: string
    provider: string
    providerAccountId: string
    refresh_token?: string | null
    access_token?: string | null
    expires_at?: number | null
    token_type?: string | null
    scope?: string | null
    id_token?: string | null
    session_state?: string | null
    user: UserCreateNestedOneWithoutAccountsInput
  }

  export type AccountUncheckedCreateInput = {
    id?: string
    userId: string
    type: string
    provider: string
    providerAccountId: string
    refresh_token?: string | null
    access_token?: string | null
    expires_at?: number | null
    token_type?: string | null
    scope?: string | null
    id_token?: string | null
    session_state?: string | null
  }

  export type AccountUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    provider?: StringFieldUpdateOperationsInput | string
    providerAccountId?: StringFieldUpdateOperationsInput | string
    refresh_token?: NullableStringFieldUpdateOperationsInput | string | null
    access_token?: NullableStringFieldUpdateOperationsInput | string | null
    expires_at?: NullableIntFieldUpdateOperationsInput | number | null
    token_type?: NullableStringFieldUpdateOperationsInput | string | null
    scope?: NullableStringFieldUpdateOperationsInput | string | null
    id_token?: NullableStringFieldUpdateOperationsInput | string | null
    session_state?: NullableStringFieldUpdateOperationsInput | string | null
    user?: UserUpdateOneRequiredWithoutAccountsNestedInput
  }

  export type AccountUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    provider?: StringFieldUpdateOperationsInput | string
    providerAccountId?: StringFieldUpdateOperationsInput | string
    refresh_token?: NullableStringFieldUpdateOperationsInput | string | null
    access_token?: NullableStringFieldUpdateOperationsInput | string | null
    expires_at?: NullableIntFieldUpdateOperationsInput | number | null
    token_type?: NullableStringFieldUpdateOperationsInput | string | null
    scope?: NullableStringFieldUpdateOperationsInput | string | null
    id_token?: NullableStringFieldUpdateOperationsInput | string | null
    session_state?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type AccountCreateManyInput = {
    id?: string
    userId: string
    type: string
    provider: string
    providerAccountId: string
    refresh_token?: string | null
    access_token?: string | null
    expires_at?: number | null
    token_type?: string | null
    scope?: string | null
    id_token?: string | null
    session_state?: string | null
  }

  export type AccountUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    provider?: StringFieldUpdateOperationsInput | string
    providerAccountId?: StringFieldUpdateOperationsInput | string
    refresh_token?: NullableStringFieldUpdateOperationsInput | string | null
    access_token?: NullableStringFieldUpdateOperationsInput | string | null
    expires_at?: NullableIntFieldUpdateOperationsInput | number | null
    token_type?: NullableStringFieldUpdateOperationsInput | string | null
    scope?: NullableStringFieldUpdateOperationsInput | string | null
    id_token?: NullableStringFieldUpdateOperationsInput | string | null
    session_state?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type AccountUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    provider?: StringFieldUpdateOperationsInput | string
    providerAccountId?: StringFieldUpdateOperationsInput | string
    refresh_token?: NullableStringFieldUpdateOperationsInput | string | null
    access_token?: NullableStringFieldUpdateOperationsInput | string | null
    expires_at?: NullableIntFieldUpdateOperationsInput | number | null
    token_type?: NullableStringFieldUpdateOperationsInput | string | null
    scope?: NullableStringFieldUpdateOperationsInput | string | null
    id_token?: NullableStringFieldUpdateOperationsInput | string | null
    session_state?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type SessionCreateInput = {
    id?: string
    sessionToken: string
    expires: Date | string
    user: UserCreateNestedOneWithoutSessionsInput
  }

  export type SessionUncheckedCreateInput = {
    id?: string
    sessionToken: string
    userId: string
    expires: Date | string
  }

  export type SessionUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    sessionToken?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
    user?: UserUpdateOneRequiredWithoutSessionsNestedInput
  }

  export type SessionUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    sessionToken?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type SessionCreateManyInput = {
    id?: string
    sessionToken: string
    userId: string
    expires: Date | string
  }

  export type SessionUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    sessionToken?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type SessionUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    sessionToken?: StringFieldUpdateOperationsInput | string
    userId?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type VerificationTokenCreateInput = {
    identifier: string
    token: string
    expires: Date | string
  }

  export type VerificationTokenUncheckedCreateInput = {
    identifier: string
    token: string
    expires: Date | string
  }

  export type VerificationTokenUpdateInput = {
    identifier?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type VerificationTokenUncheckedUpdateInput = {
    identifier?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type VerificationTokenCreateManyInput = {
    identifier: string
    token: string
    expires: Date | string
  }

  export type VerificationTokenUpdateManyMutationInput = {
    identifier?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type VerificationTokenUncheckedUpdateManyInput = {
    identifier?: StringFieldUpdateOperationsInput | string
    token?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type SportCreateInput = {
    id?: string
    key: string
    name: string
    createdAt?: Date | string
    updatedAt?: Date | string
    teams?: TeamCreateNestedManyWithoutSportInput
    games?: GameCreateNestedManyWithoutSportInput
  }

  export type SportUncheckedCreateInput = {
    id?: string
    key: string
    name: string
    createdAt?: Date | string
    updatedAt?: Date | string
    teams?: TeamUncheckedCreateNestedManyWithoutSportInput
    games?: GameUncheckedCreateNestedManyWithoutSportInput
  }

  export type SportUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    key?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    teams?: TeamUpdateManyWithoutSportNestedInput
    games?: GameUpdateManyWithoutSportNestedInput
  }

  export type SportUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    key?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    teams?: TeamUncheckedUpdateManyWithoutSportNestedInput
    games?: GameUncheckedUpdateManyWithoutSportNestedInput
  }

  export type SportCreateManyInput = {
    id?: string
    key: string
    name: string
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type SportUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    key?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type SportUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    key?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TeamCreateInput = {
    id?: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutTeamsInput
    homeGames?: GameCreateNestedManyWithoutHomeTeamInput
    awayGames?: GameCreateNestedManyWithoutAwayTeamInput
    injuries?: InjuryCreateNestedManyWithoutTeamInput
    profiles?: TeamProfileWeeklyCreateNestedManyWithoutTeamInput
  }

  export type TeamUncheckedCreateInput = {
    id?: string
    sportId: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    homeGames?: GameUncheckedCreateNestedManyWithoutHomeTeamInput
    awayGames?: GameUncheckedCreateNestedManyWithoutAwayTeamInput
    injuries?: InjuryUncheckedCreateNestedManyWithoutTeamInput
    profiles?: TeamProfileWeeklyUncheckedCreateNestedManyWithoutTeamInput
  }

  export type TeamUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutTeamsNestedInput
    homeGames?: GameUpdateManyWithoutHomeTeamNestedInput
    awayGames?: GameUpdateManyWithoutAwayTeamNestedInput
    injuries?: InjuryUpdateManyWithoutTeamNestedInput
    profiles?: TeamProfileWeeklyUpdateManyWithoutTeamNestedInput
  }

  export type TeamUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    homeGames?: GameUncheckedUpdateManyWithoutHomeTeamNestedInput
    awayGames?: GameUncheckedUpdateManyWithoutAwayTeamNestedInput
    injuries?: InjuryUncheckedUpdateManyWithoutTeamNestedInput
    profiles?: TeamProfileWeeklyUncheckedUpdateManyWithoutTeamNestedInput
  }

  export type TeamCreateManyInput = {
    id?: string
    sportId: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type TeamUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TeamUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type GameCreateInput = {
    id?: string
    date: Date | string
    slug: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutGamesInput
    homeTeam: TeamCreateNestedOneWithoutHomeGamesInput
    awayTeam: TeamCreateNestedOneWithoutAwayGamesInput
    market?: MarketSnapshotCreateNestedOneWithoutGameInput
    model?: ModelProjectionCreateNestedOneWithoutGameInput
    writeup?: WriteupCreateNestedOneWithoutGameInput
  }

  export type GameUncheckedCreateInput = {
    id?: string
    sportId: string
    date: Date | string
    slug: string
    homeTeamId: string
    awayTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    market?: MarketSnapshotUncheckedCreateNestedOneWithoutGameInput
    model?: ModelProjectionUncheckedCreateNestedOneWithoutGameInput
    writeup?: WriteupUncheckedCreateNestedOneWithoutGameInput
  }

  export type GameUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutGamesNestedInput
    homeTeam?: TeamUpdateOneRequiredWithoutHomeGamesNestedInput
    awayTeam?: TeamUpdateOneRequiredWithoutAwayGamesNestedInput
    market?: MarketSnapshotUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUpdateOneWithoutGameNestedInput
    writeup?: WriteupUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    homeTeamId?: StringFieldUpdateOperationsInput | string
    awayTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    market?: MarketSnapshotUncheckedUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUncheckedUpdateOneWithoutGameNestedInput
    writeup?: WriteupUncheckedUpdateOneWithoutGameNestedInput
  }

  export type GameCreateManyInput = {
    id?: string
    sportId: string
    date: Date | string
    slug: string
    homeTeamId: string
    awayTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type GameUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type GameUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    homeTeamId?: StringFieldUpdateOperationsInput | string
    awayTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type MarketSnapshotCreateInput = {
    id?: string
    capturedAt?: Date | string
    openSpreadHome?: number | null
    currentSpreadHome?: number | null
    openTotal?: number | null
    currentTotal?: number | null
    bestSpreadHome?: number | null
    bestSpreadBook?: string | null
    bestTotal?: number | null
    bestTotalBook?: string | null
    spreadDispersion?: number | null
    totalDispersion?: number | null
    bookLines?: BookLineCreateNestedManyWithoutMarketInput
    game: GameCreateNestedOneWithoutMarketInput
  }

  export type MarketSnapshotUncheckedCreateInput = {
    id?: string
    gameId: string
    capturedAt?: Date | string
    openSpreadHome?: number | null
    currentSpreadHome?: number | null
    openTotal?: number | null
    currentTotal?: number | null
    bestSpreadHome?: number | null
    bestSpreadBook?: string | null
    bestTotal?: number | null
    bestTotalBook?: string | null
    spreadDispersion?: number | null
    totalDispersion?: number | null
    bookLines?: BookLineUncheckedCreateNestedManyWithoutMarketInput
  }

  export type MarketSnapshotUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    openSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    currentSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    openTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    currentTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadBook?: NullableStringFieldUpdateOperationsInput | string | null
    bestTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestTotalBook?: NullableStringFieldUpdateOperationsInput | string | null
    spreadDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    totalDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    bookLines?: BookLineUpdateManyWithoutMarketNestedInput
    game?: GameUpdateOneRequiredWithoutMarketNestedInput
  }

  export type MarketSnapshotUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    gameId?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    openSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    currentSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    openTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    currentTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadBook?: NullableStringFieldUpdateOperationsInput | string | null
    bestTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestTotalBook?: NullableStringFieldUpdateOperationsInput | string | null
    spreadDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    totalDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    bookLines?: BookLineUncheckedUpdateManyWithoutMarketNestedInput
  }

  export type MarketSnapshotCreateManyInput = {
    id?: string
    gameId: string
    capturedAt?: Date | string
    openSpreadHome?: number | null
    currentSpreadHome?: number | null
    openTotal?: number | null
    currentTotal?: number | null
    bestSpreadHome?: number | null
    bestSpreadBook?: string | null
    bestTotal?: number | null
    bestTotalBook?: string | null
    spreadDispersion?: number | null
    totalDispersion?: number | null
  }

  export type MarketSnapshotUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    openSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    currentSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    openTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    currentTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadBook?: NullableStringFieldUpdateOperationsInput | string | null
    bestTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestTotalBook?: NullableStringFieldUpdateOperationsInput | string | null
    spreadDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    totalDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
  }

  export type MarketSnapshotUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    gameId?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    openSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    currentSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    openTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    currentTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadBook?: NullableStringFieldUpdateOperationsInput | string | null
    bestTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestTotalBook?: NullableStringFieldUpdateOperationsInput | string | null
    spreadDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    totalDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
  }

  export type BookLineCreateInput = {
    id?: string
    book: string
    capturedAt?: Date | string
    spreadHome?: number | null
    spreadAway?: number | null
    total?: number | null
    market: MarketSnapshotCreateNestedOneWithoutBookLinesInput
  }

  export type BookLineUncheckedCreateInput = {
    id?: string
    marketId: string
    book: string
    capturedAt?: Date | string
    spreadHome?: number | null
    spreadAway?: number | null
    total?: number | null
  }

  export type BookLineUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    book?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    spreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    spreadAway?: NullableFloatFieldUpdateOperationsInput | number | null
    total?: NullableFloatFieldUpdateOperationsInput | number | null
    market?: MarketSnapshotUpdateOneRequiredWithoutBookLinesNestedInput
  }

  export type BookLineUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    marketId?: StringFieldUpdateOperationsInput | string
    book?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    spreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    spreadAway?: NullableFloatFieldUpdateOperationsInput | number | null
    total?: NullableFloatFieldUpdateOperationsInput | number | null
  }

  export type BookLineCreateManyInput = {
    id?: string
    marketId: string
    book: string
    capturedAt?: Date | string
    spreadHome?: number | null
    spreadAway?: number | null
    total?: number | null
  }

  export type BookLineUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    book?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    spreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    spreadAway?: NullableFloatFieldUpdateOperationsInput | number | null
    total?: NullableFloatFieldUpdateOperationsInput | number | null
  }

  export type BookLineUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    marketId?: StringFieldUpdateOperationsInput | string
    book?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    spreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    spreadAway?: NullableFloatFieldUpdateOperationsInput | number | null
    total?: NullableFloatFieldUpdateOperationsInput | number | null
  }

  export type ModelProjectionCreateInput = {
    id?: string
    version: string
    computedAt?: Date | string
    projSpreadHome: number
    projTotal: number
    game: GameCreateNestedOneWithoutModelInput
  }

  export type ModelProjectionUncheckedCreateInput = {
    id?: string
    gameId: string
    version: string
    computedAt?: Date | string
    projSpreadHome: number
    projTotal: number
  }

  export type ModelProjectionUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    version?: StringFieldUpdateOperationsInput | string
    computedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    projSpreadHome?: FloatFieldUpdateOperationsInput | number
    projTotal?: FloatFieldUpdateOperationsInput | number
    game?: GameUpdateOneRequiredWithoutModelNestedInput
  }

  export type ModelProjectionUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    gameId?: StringFieldUpdateOperationsInput | string
    version?: StringFieldUpdateOperationsInput | string
    computedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    projSpreadHome?: FloatFieldUpdateOperationsInput | number
    projTotal?: FloatFieldUpdateOperationsInput | number
  }

  export type ModelProjectionCreateManyInput = {
    id?: string
    gameId: string
    version: string
    computedAt?: Date | string
    projSpreadHome: number
    projTotal: number
  }

  export type ModelProjectionUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    version?: StringFieldUpdateOperationsInput | string
    computedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    projSpreadHome?: FloatFieldUpdateOperationsInput | number
    projTotal?: FloatFieldUpdateOperationsInput | number
  }

  export type ModelProjectionUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    gameId?: StringFieldUpdateOperationsInput | string
    version?: StringFieldUpdateOperationsInput | string
    computedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    projSpreadHome?: FloatFieldUpdateOperationsInput | number
    projTotal?: FloatFieldUpdateOperationsInput | number
  }

  export type WriteupCreateInput = {
    id?: string
    createdAt?: Date | string
    updatedAt?: Date | string
    formatKey: string
    body: string
    disclosedAi?: boolean
    editorStatus?: $Enums.EditorStatus
    game: GameCreateNestedOneWithoutWriteupInput
  }

  export type WriteupUncheckedCreateInput = {
    id?: string
    gameId: string
    createdAt?: Date | string
    updatedAt?: Date | string
    formatKey: string
    body: string
    disclosedAi?: boolean
    editorStatus?: $Enums.EditorStatus
  }

  export type WriteupUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    formatKey?: StringFieldUpdateOperationsInput | string
    body?: StringFieldUpdateOperationsInput | string
    disclosedAi?: BoolFieldUpdateOperationsInput | boolean
    editorStatus?: EnumEditorStatusFieldUpdateOperationsInput | $Enums.EditorStatus
    game?: GameUpdateOneRequiredWithoutWriteupNestedInput
  }

  export type WriteupUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    gameId?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    formatKey?: StringFieldUpdateOperationsInput | string
    body?: StringFieldUpdateOperationsInput | string
    disclosedAi?: BoolFieldUpdateOperationsInput | boolean
    editorStatus?: EnumEditorStatusFieldUpdateOperationsInput | $Enums.EditorStatus
  }

  export type WriteupCreateManyInput = {
    id?: string
    gameId: string
    createdAt?: Date | string
    updatedAt?: Date | string
    formatKey: string
    body: string
    disclosedAi?: boolean
    editorStatus?: $Enums.EditorStatus
  }

  export type WriteupUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    formatKey?: StringFieldUpdateOperationsInput | string
    body?: StringFieldUpdateOperationsInput | string
    disclosedAi?: BoolFieldUpdateOperationsInput | boolean
    editorStatus?: EnumEditorStatusFieldUpdateOperationsInput | $Enums.EditorStatus
  }

  export type WriteupUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    gameId?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    formatKey?: StringFieldUpdateOperationsInput | string
    body?: StringFieldUpdateOperationsInput | string
    disclosedAi?: BoolFieldUpdateOperationsInput | boolean
    editorStatus?: EnumEditorStatusFieldUpdateOperationsInput | $Enums.EditorStatus
  }

  export type InjuryCreateInput = {
    id?: string
    date: Date | string
    player: string
    status: $Enums.InjuryStatus
    note?: string | null
    impact?: $Enums.InjuryImpact | null
    createdAt?: Date | string
    updatedAt?: Date | string
    team: TeamCreateNestedOneWithoutInjuriesInput
  }

  export type InjuryUncheckedCreateInput = {
    id?: string
    teamId: string
    date: Date | string
    player: string
    status: $Enums.InjuryStatus
    note?: string | null
    impact?: $Enums.InjuryImpact | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type InjuryUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    player?: StringFieldUpdateOperationsInput | string
    status?: EnumInjuryStatusFieldUpdateOperationsInput | $Enums.InjuryStatus
    note?: NullableStringFieldUpdateOperationsInput | string | null
    impact?: NullableEnumInjuryImpactFieldUpdateOperationsInput | $Enums.InjuryImpact | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    team?: TeamUpdateOneRequiredWithoutInjuriesNestedInput
  }

  export type InjuryUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    teamId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    player?: StringFieldUpdateOperationsInput | string
    status?: EnumInjuryStatusFieldUpdateOperationsInput | $Enums.InjuryStatus
    note?: NullableStringFieldUpdateOperationsInput | string | null
    impact?: NullableEnumInjuryImpactFieldUpdateOperationsInput | $Enums.InjuryImpact | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type InjuryCreateManyInput = {
    id?: string
    teamId: string
    date: Date | string
    player: string
    status: $Enums.InjuryStatus
    note?: string | null
    impact?: $Enums.InjuryImpact | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type InjuryUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    player?: StringFieldUpdateOperationsInput | string
    status?: EnumInjuryStatusFieldUpdateOperationsInput | $Enums.InjuryStatus
    note?: NullableStringFieldUpdateOperationsInput | string | null
    impact?: NullableEnumInjuryImpactFieldUpdateOperationsInput | $Enums.InjuryImpact | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type InjuryUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    teamId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    player?: StringFieldUpdateOperationsInput | string
    status?: EnumInjuryStatusFieldUpdateOperationsInput | $Enums.InjuryStatus
    note?: NullableStringFieldUpdateOperationsInput | string | null
    impact?: NullableEnumInjuryImpactFieldUpdateOperationsInput | $Enums.InjuryImpact | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TeamProfileWeeklyCreateInput = {
    id?: string
    weekStart: Date | string
    summary: string
    tempoRank?: number | null
    offPpp?: number | null
    defPpp?: number | null
    createdAt?: Date | string
    updatedAt?: Date | string
    team: TeamCreateNestedOneWithoutProfilesInput
  }

  export type TeamProfileWeeklyUncheckedCreateInput = {
    id?: string
    teamId: string
    weekStart: Date | string
    summary: string
    tempoRank?: number | null
    offPpp?: number | null
    defPpp?: number | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type TeamProfileWeeklyUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    weekStart?: DateTimeFieldUpdateOperationsInput | Date | string
    summary?: StringFieldUpdateOperationsInput | string
    tempoRank?: NullableIntFieldUpdateOperationsInput | number | null
    offPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    defPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    team?: TeamUpdateOneRequiredWithoutProfilesNestedInput
  }

  export type TeamProfileWeeklyUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    teamId?: StringFieldUpdateOperationsInput | string
    weekStart?: DateTimeFieldUpdateOperationsInput | Date | string
    summary?: StringFieldUpdateOperationsInput | string
    tempoRank?: NullableIntFieldUpdateOperationsInput | number | null
    offPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    defPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TeamProfileWeeklyCreateManyInput = {
    id?: string
    teamId: string
    weekStart: Date | string
    summary: string
    tempoRank?: number | null
    offPpp?: number | null
    defPpp?: number | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type TeamProfileWeeklyUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    weekStart?: DateTimeFieldUpdateOperationsInput | Date | string
    summary?: StringFieldUpdateOperationsInput | string
    tempoRank?: NullableIntFieldUpdateOperationsInput | number | null
    offPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    defPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TeamProfileWeeklyUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    teamId?: StringFieldUpdateOperationsInput | string
    weekStart?: DateTimeFieldUpdateOperationsInput | Date | string
    summary?: StringFieldUpdateOperationsInput | string
    tempoRank?: NullableIntFieldUpdateOperationsInput | number | null
    offPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    defPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type StringFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringFilter<$PrismaModel> | string
  }

  export type DateTimeNullableFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableFilter<$PrismaModel> | Date | string | null
  }

  export type StringNullableFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringNullableFilter<$PrismaModel> | string | null
  }

  export type EnumUserRoleFilter<$PrismaModel = never> = {
    equals?: $Enums.UserRole | EnumUserRoleFieldRefInput<$PrismaModel>
    in?: $Enums.UserRole[] | ListEnumUserRoleFieldRefInput<$PrismaModel>
    notIn?: $Enums.UserRole[] | ListEnumUserRoleFieldRefInput<$PrismaModel>
    not?: NestedEnumUserRoleFilter<$PrismaModel> | $Enums.UserRole
  }

  export type EnumSubscriptionStatusNullableFilter<$PrismaModel = never> = {
    equals?: $Enums.SubscriptionStatus | EnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    in?: $Enums.SubscriptionStatus[] | ListEnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    notIn?: $Enums.SubscriptionStatus[] | ListEnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    not?: NestedEnumSubscriptionStatusNullableFilter<$PrismaModel> | $Enums.SubscriptionStatus | null
  }

  export type DateTimeFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeFilter<$PrismaModel> | Date | string
  }

  export type AccountListRelationFilter = {
    every?: AccountWhereInput
    some?: AccountWhereInput
    none?: AccountWhereInput
  }

  export type SessionListRelationFilter = {
    every?: SessionWhereInput
    some?: SessionWhereInput
    none?: SessionWhereInput
  }

  export type SortOrderInput = {
    sort: SortOrder
    nulls?: NullsOrder
  }

  export type AccountOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type SessionOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type UserCountOrderByAggregateInput = {
    id?: SortOrder
    email?: SortOrder
    emailVerified?: SortOrder
    name?: SortOrder
    password?: SortOrder
    image?: SortOrder
    role?: SortOrder
    subscriptionStatus?: SortOrder
    subscriptionPlan?: SortOrder
    subscriptionStart?: SortOrder
    subscriptionEnd?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type UserMaxOrderByAggregateInput = {
    id?: SortOrder
    email?: SortOrder
    emailVerified?: SortOrder
    name?: SortOrder
    password?: SortOrder
    image?: SortOrder
    role?: SortOrder
    subscriptionStatus?: SortOrder
    subscriptionPlan?: SortOrder
    subscriptionStart?: SortOrder
    subscriptionEnd?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type UserMinOrderByAggregateInput = {
    id?: SortOrder
    email?: SortOrder
    emailVerified?: SortOrder
    name?: SortOrder
    password?: SortOrder
    image?: SortOrder
    role?: SortOrder
    subscriptionStatus?: SortOrder
    subscriptionPlan?: SortOrder
    subscriptionStart?: SortOrder
    subscriptionEnd?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type StringWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringWithAggregatesFilter<$PrismaModel> | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedStringFilter<$PrismaModel>
    _max?: NestedStringFilter<$PrismaModel>
  }

  export type DateTimeNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableWithAggregatesFilter<$PrismaModel> | Date | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedDateTimeNullableFilter<$PrismaModel>
    _max?: NestedDateTimeNullableFilter<$PrismaModel>
  }

  export type StringNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringNullableWithAggregatesFilter<$PrismaModel> | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedStringNullableFilter<$PrismaModel>
    _max?: NestedStringNullableFilter<$PrismaModel>
  }

  export type EnumUserRoleWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.UserRole | EnumUserRoleFieldRefInput<$PrismaModel>
    in?: $Enums.UserRole[] | ListEnumUserRoleFieldRefInput<$PrismaModel>
    notIn?: $Enums.UserRole[] | ListEnumUserRoleFieldRefInput<$PrismaModel>
    not?: NestedEnumUserRoleWithAggregatesFilter<$PrismaModel> | $Enums.UserRole
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumUserRoleFilter<$PrismaModel>
    _max?: NestedEnumUserRoleFilter<$PrismaModel>
  }

  export type EnumSubscriptionStatusNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.SubscriptionStatus | EnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    in?: $Enums.SubscriptionStatus[] | ListEnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    notIn?: $Enums.SubscriptionStatus[] | ListEnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    not?: NestedEnumSubscriptionStatusNullableWithAggregatesFilter<$PrismaModel> | $Enums.SubscriptionStatus | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedEnumSubscriptionStatusNullableFilter<$PrismaModel>
    _max?: NestedEnumSubscriptionStatusNullableFilter<$PrismaModel>
  }

  export type DateTimeWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeWithAggregatesFilter<$PrismaModel> | Date | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedDateTimeFilter<$PrismaModel>
    _max?: NestedDateTimeFilter<$PrismaModel>
  }

  export type IntNullableFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel> | null
    in?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntNullableFilter<$PrismaModel> | number | null
  }

  export type UserScalarRelationFilter = {
    is?: UserWhereInput
    isNot?: UserWhereInput
  }

  export type AccountProviderProviderAccountIdCompoundUniqueInput = {
    provider: string
    providerAccountId: string
  }

  export type AccountCountOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    type?: SortOrder
    provider?: SortOrder
    providerAccountId?: SortOrder
    refresh_token?: SortOrder
    access_token?: SortOrder
    expires_at?: SortOrder
    token_type?: SortOrder
    scope?: SortOrder
    id_token?: SortOrder
    session_state?: SortOrder
  }

  export type AccountAvgOrderByAggregateInput = {
    expires_at?: SortOrder
  }

  export type AccountMaxOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    type?: SortOrder
    provider?: SortOrder
    providerAccountId?: SortOrder
    refresh_token?: SortOrder
    access_token?: SortOrder
    expires_at?: SortOrder
    token_type?: SortOrder
    scope?: SortOrder
    id_token?: SortOrder
    session_state?: SortOrder
  }

  export type AccountMinOrderByAggregateInput = {
    id?: SortOrder
    userId?: SortOrder
    type?: SortOrder
    provider?: SortOrder
    providerAccountId?: SortOrder
    refresh_token?: SortOrder
    access_token?: SortOrder
    expires_at?: SortOrder
    token_type?: SortOrder
    scope?: SortOrder
    id_token?: SortOrder
    session_state?: SortOrder
  }

  export type AccountSumOrderByAggregateInput = {
    expires_at?: SortOrder
  }

  export type IntNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel> | null
    in?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntNullableWithAggregatesFilter<$PrismaModel> | number | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _avg?: NestedFloatNullableFilter<$PrismaModel>
    _sum?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedIntNullableFilter<$PrismaModel>
    _max?: NestedIntNullableFilter<$PrismaModel>
  }

  export type SessionCountOrderByAggregateInput = {
    id?: SortOrder
    sessionToken?: SortOrder
    userId?: SortOrder
    expires?: SortOrder
  }

  export type SessionMaxOrderByAggregateInput = {
    id?: SortOrder
    sessionToken?: SortOrder
    userId?: SortOrder
    expires?: SortOrder
  }

  export type SessionMinOrderByAggregateInput = {
    id?: SortOrder
    sessionToken?: SortOrder
    userId?: SortOrder
    expires?: SortOrder
  }

  export type VerificationTokenIdentifierTokenCompoundUniqueInput = {
    identifier: string
    token: string
  }

  export type VerificationTokenCountOrderByAggregateInput = {
    identifier?: SortOrder
    token?: SortOrder
    expires?: SortOrder
  }

  export type VerificationTokenMaxOrderByAggregateInput = {
    identifier?: SortOrder
    token?: SortOrder
    expires?: SortOrder
  }

  export type VerificationTokenMinOrderByAggregateInput = {
    identifier?: SortOrder
    token?: SortOrder
    expires?: SortOrder
  }

  export type TeamListRelationFilter = {
    every?: TeamWhereInput
    some?: TeamWhereInput
    none?: TeamWhereInput
  }

  export type GameListRelationFilter = {
    every?: GameWhereInput
    some?: GameWhereInput
    none?: GameWhereInput
  }

  export type TeamOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type GameOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type SportCountOrderByAggregateInput = {
    id?: SortOrder
    key?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type SportMaxOrderByAggregateInput = {
    id?: SortOrder
    key?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type SportMinOrderByAggregateInput = {
    id?: SortOrder
    key?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type SportScalarRelationFilter = {
    is?: SportWhereInput
    isNot?: SportWhereInput
  }

  export type InjuryListRelationFilter = {
    every?: InjuryWhereInput
    some?: InjuryWhereInput
    none?: InjuryWhereInput
  }

  export type TeamProfileWeeklyListRelationFilter = {
    every?: TeamProfileWeeklyWhereInput
    some?: TeamProfileWeeklyWhereInput
    none?: TeamProfileWeeklyWhereInput
  }

  export type InjuryOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type TeamProfileWeeklyOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type TeamSportIdSlugCompoundUniqueInput = {
    sportId: string
    slug: string
  }

  export type TeamCountOrderByAggregateInput = {
    id?: SortOrder
    sportId?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    abbr?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type TeamMaxOrderByAggregateInput = {
    id?: SortOrder
    sportId?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    abbr?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type TeamMinOrderByAggregateInput = {
    id?: SortOrder
    sportId?: SortOrder
    name?: SortOrder
    slug?: SortOrder
    abbr?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type TeamScalarRelationFilter = {
    is?: TeamWhereInput
    isNot?: TeamWhereInput
  }

  export type MarketSnapshotNullableScalarRelationFilter = {
    is?: MarketSnapshotWhereInput | null
    isNot?: MarketSnapshotWhereInput | null
  }

  export type ModelProjectionNullableScalarRelationFilter = {
    is?: ModelProjectionWhereInput | null
    isNot?: ModelProjectionWhereInput | null
  }

  export type WriteupNullableScalarRelationFilter = {
    is?: WriteupWhereInput | null
    isNot?: WriteupWhereInput | null
  }

  export type GameSportIdDateSlugCompoundUniqueInput = {
    sportId: string
    date: Date | string
    slug: string
  }

  export type GameCountOrderByAggregateInput = {
    id?: SortOrder
    sportId?: SortOrder
    date?: SortOrder
    slug?: SortOrder
    homeTeamId?: SortOrder
    awayTeamId?: SortOrder
    startTime?: SortOrder
    venue?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type GameMaxOrderByAggregateInput = {
    id?: SortOrder
    sportId?: SortOrder
    date?: SortOrder
    slug?: SortOrder
    homeTeamId?: SortOrder
    awayTeamId?: SortOrder
    startTime?: SortOrder
    venue?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type GameMinOrderByAggregateInput = {
    id?: SortOrder
    sportId?: SortOrder
    date?: SortOrder
    slug?: SortOrder
    homeTeamId?: SortOrder
    awayTeamId?: SortOrder
    startTime?: SortOrder
    venue?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type FloatNullableFilter<$PrismaModel = never> = {
    equals?: number | FloatFieldRefInput<$PrismaModel> | null
    in?: number[] | ListFloatFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListFloatFieldRefInput<$PrismaModel> | null
    lt?: number | FloatFieldRefInput<$PrismaModel>
    lte?: number | FloatFieldRefInput<$PrismaModel>
    gt?: number | FloatFieldRefInput<$PrismaModel>
    gte?: number | FloatFieldRefInput<$PrismaModel>
    not?: NestedFloatNullableFilter<$PrismaModel> | number | null
  }

  export type BookLineListRelationFilter = {
    every?: BookLineWhereInput
    some?: BookLineWhereInput
    none?: BookLineWhereInput
  }

  export type GameScalarRelationFilter = {
    is?: GameWhereInput
    isNot?: GameWhereInput
  }

  export type BookLineOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type MarketSnapshotCountOrderByAggregateInput = {
    id?: SortOrder
    gameId?: SortOrder
    capturedAt?: SortOrder
    openSpreadHome?: SortOrder
    currentSpreadHome?: SortOrder
    openTotal?: SortOrder
    currentTotal?: SortOrder
    bestSpreadHome?: SortOrder
    bestSpreadBook?: SortOrder
    bestTotal?: SortOrder
    bestTotalBook?: SortOrder
    spreadDispersion?: SortOrder
    totalDispersion?: SortOrder
  }

  export type MarketSnapshotAvgOrderByAggregateInput = {
    openSpreadHome?: SortOrder
    currentSpreadHome?: SortOrder
    openTotal?: SortOrder
    currentTotal?: SortOrder
    bestSpreadHome?: SortOrder
    bestTotal?: SortOrder
    spreadDispersion?: SortOrder
    totalDispersion?: SortOrder
  }

  export type MarketSnapshotMaxOrderByAggregateInput = {
    id?: SortOrder
    gameId?: SortOrder
    capturedAt?: SortOrder
    openSpreadHome?: SortOrder
    currentSpreadHome?: SortOrder
    openTotal?: SortOrder
    currentTotal?: SortOrder
    bestSpreadHome?: SortOrder
    bestSpreadBook?: SortOrder
    bestTotal?: SortOrder
    bestTotalBook?: SortOrder
    spreadDispersion?: SortOrder
    totalDispersion?: SortOrder
  }

  export type MarketSnapshotMinOrderByAggregateInput = {
    id?: SortOrder
    gameId?: SortOrder
    capturedAt?: SortOrder
    openSpreadHome?: SortOrder
    currentSpreadHome?: SortOrder
    openTotal?: SortOrder
    currentTotal?: SortOrder
    bestSpreadHome?: SortOrder
    bestSpreadBook?: SortOrder
    bestTotal?: SortOrder
    bestTotalBook?: SortOrder
    spreadDispersion?: SortOrder
    totalDispersion?: SortOrder
  }

  export type MarketSnapshotSumOrderByAggregateInput = {
    openSpreadHome?: SortOrder
    currentSpreadHome?: SortOrder
    openTotal?: SortOrder
    currentTotal?: SortOrder
    bestSpreadHome?: SortOrder
    bestTotal?: SortOrder
    spreadDispersion?: SortOrder
    totalDispersion?: SortOrder
  }

  export type FloatNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: number | FloatFieldRefInput<$PrismaModel> | null
    in?: number[] | ListFloatFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListFloatFieldRefInput<$PrismaModel> | null
    lt?: number | FloatFieldRefInput<$PrismaModel>
    lte?: number | FloatFieldRefInput<$PrismaModel>
    gt?: number | FloatFieldRefInput<$PrismaModel>
    gte?: number | FloatFieldRefInput<$PrismaModel>
    not?: NestedFloatNullableWithAggregatesFilter<$PrismaModel> | number | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _avg?: NestedFloatNullableFilter<$PrismaModel>
    _sum?: NestedFloatNullableFilter<$PrismaModel>
    _min?: NestedFloatNullableFilter<$PrismaModel>
    _max?: NestedFloatNullableFilter<$PrismaModel>
  }

  export type MarketSnapshotScalarRelationFilter = {
    is?: MarketSnapshotWhereInput
    isNot?: MarketSnapshotWhereInput
  }

  export type BookLineCountOrderByAggregateInput = {
    id?: SortOrder
    marketId?: SortOrder
    book?: SortOrder
    capturedAt?: SortOrder
    spreadHome?: SortOrder
    spreadAway?: SortOrder
    total?: SortOrder
  }

  export type BookLineAvgOrderByAggregateInput = {
    spreadHome?: SortOrder
    spreadAway?: SortOrder
    total?: SortOrder
  }

  export type BookLineMaxOrderByAggregateInput = {
    id?: SortOrder
    marketId?: SortOrder
    book?: SortOrder
    capturedAt?: SortOrder
    spreadHome?: SortOrder
    spreadAway?: SortOrder
    total?: SortOrder
  }

  export type BookLineMinOrderByAggregateInput = {
    id?: SortOrder
    marketId?: SortOrder
    book?: SortOrder
    capturedAt?: SortOrder
    spreadHome?: SortOrder
    spreadAway?: SortOrder
    total?: SortOrder
  }

  export type BookLineSumOrderByAggregateInput = {
    spreadHome?: SortOrder
    spreadAway?: SortOrder
    total?: SortOrder
  }

  export type FloatFilter<$PrismaModel = never> = {
    equals?: number | FloatFieldRefInput<$PrismaModel>
    in?: number[] | ListFloatFieldRefInput<$PrismaModel>
    notIn?: number[] | ListFloatFieldRefInput<$PrismaModel>
    lt?: number | FloatFieldRefInput<$PrismaModel>
    lte?: number | FloatFieldRefInput<$PrismaModel>
    gt?: number | FloatFieldRefInput<$PrismaModel>
    gte?: number | FloatFieldRefInput<$PrismaModel>
    not?: NestedFloatFilter<$PrismaModel> | number
  }

  export type ModelProjectionCountOrderByAggregateInput = {
    id?: SortOrder
    gameId?: SortOrder
    version?: SortOrder
    computedAt?: SortOrder
    projSpreadHome?: SortOrder
    projTotal?: SortOrder
  }

  export type ModelProjectionAvgOrderByAggregateInput = {
    projSpreadHome?: SortOrder
    projTotal?: SortOrder
  }

  export type ModelProjectionMaxOrderByAggregateInput = {
    id?: SortOrder
    gameId?: SortOrder
    version?: SortOrder
    computedAt?: SortOrder
    projSpreadHome?: SortOrder
    projTotal?: SortOrder
  }

  export type ModelProjectionMinOrderByAggregateInput = {
    id?: SortOrder
    gameId?: SortOrder
    version?: SortOrder
    computedAt?: SortOrder
    projSpreadHome?: SortOrder
    projTotal?: SortOrder
  }

  export type ModelProjectionSumOrderByAggregateInput = {
    projSpreadHome?: SortOrder
    projTotal?: SortOrder
  }

  export type FloatWithAggregatesFilter<$PrismaModel = never> = {
    equals?: number | FloatFieldRefInput<$PrismaModel>
    in?: number[] | ListFloatFieldRefInput<$PrismaModel>
    notIn?: number[] | ListFloatFieldRefInput<$PrismaModel>
    lt?: number | FloatFieldRefInput<$PrismaModel>
    lte?: number | FloatFieldRefInput<$PrismaModel>
    gt?: number | FloatFieldRefInput<$PrismaModel>
    gte?: number | FloatFieldRefInput<$PrismaModel>
    not?: NestedFloatWithAggregatesFilter<$PrismaModel> | number
    _count?: NestedIntFilter<$PrismaModel>
    _avg?: NestedFloatFilter<$PrismaModel>
    _sum?: NestedFloatFilter<$PrismaModel>
    _min?: NestedFloatFilter<$PrismaModel>
    _max?: NestedFloatFilter<$PrismaModel>
  }

  export type BoolFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolFilter<$PrismaModel> | boolean
  }

  export type EnumEditorStatusFilter<$PrismaModel = never> = {
    equals?: $Enums.EditorStatus | EnumEditorStatusFieldRefInput<$PrismaModel>
    in?: $Enums.EditorStatus[] | ListEnumEditorStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.EditorStatus[] | ListEnumEditorStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumEditorStatusFilter<$PrismaModel> | $Enums.EditorStatus
  }

  export type WriteupCountOrderByAggregateInput = {
    id?: SortOrder
    gameId?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    formatKey?: SortOrder
    body?: SortOrder
    disclosedAi?: SortOrder
    editorStatus?: SortOrder
  }

  export type WriteupMaxOrderByAggregateInput = {
    id?: SortOrder
    gameId?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    formatKey?: SortOrder
    body?: SortOrder
    disclosedAi?: SortOrder
    editorStatus?: SortOrder
  }

  export type WriteupMinOrderByAggregateInput = {
    id?: SortOrder
    gameId?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
    formatKey?: SortOrder
    body?: SortOrder
    disclosedAi?: SortOrder
    editorStatus?: SortOrder
  }

  export type BoolWithAggregatesFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolWithAggregatesFilter<$PrismaModel> | boolean
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedBoolFilter<$PrismaModel>
    _max?: NestedBoolFilter<$PrismaModel>
  }

  export type EnumEditorStatusWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.EditorStatus | EnumEditorStatusFieldRefInput<$PrismaModel>
    in?: $Enums.EditorStatus[] | ListEnumEditorStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.EditorStatus[] | ListEnumEditorStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumEditorStatusWithAggregatesFilter<$PrismaModel> | $Enums.EditorStatus
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumEditorStatusFilter<$PrismaModel>
    _max?: NestedEnumEditorStatusFilter<$PrismaModel>
  }

  export type EnumInjuryStatusFilter<$PrismaModel = never> = {
    equals?: $Enums.InjuryStatus | EnumInjuryStatusFieldRefInput<$PrismaModel>
    in?: $Enums.InjuryStatus[] | ListEnumInjuryStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.InjuryStatus[] | ListEnumInjuryStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumInjuryStatusFilter<$PrismaModel> | $Enums.InjuryStatus
  }

  export type EnumInjuryImpactNullableFilter<$PrismaModel = never> = {
    equals?: $Enums.InjuryImpact | EnumInjuryImpactFieldRefInput<$PrismaModel> | null
    in?: $Enums.InjuryImpact[] | ListEnumInjuryImpactFieldRefInput<$PrismaModel> | null
    notIn?: $Enums.InjuryImpact[] | ListEnumInjuryImpactFieldRefInput<$PrismaModel> | null
    not?: NestedEnumInjuryImpactNullableFilter<$PrismaModel> | $Enums.InjuryImpact | null
  }

  export type InjuryCountOrderByAggregateInput = {
    id?: SortOrder
    teamId?: SortOrder
    date?: SortOrder
    player?: SortOrder
    status?: SortOrder
    note?: SortOrder
    impact?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type InjuryMaxOrderByAggregateInput = {
    id?: SortOrder
    teamId?: SortOrder
    date?: SortOrder
    player?: SortOrder
    status?: SortOrder
    note?: SortOrder
    impact?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type InjuryMinOrderByAggregateInput = {
    id?: SortOrder
    teamId?: SortOrder
    date?: SortOrder
    player?: SortOrder
    status?: SortOrder
    note?: SortOrder
    impact?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type EnumInjuryStatusWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.InjuryStatus | EnumInjuryStatusFieldRefInput<$PrismaModel>
    in?: $Enums.InjuryStatus[] | ListEnumInjuryStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.InjuryStatus[] | ListEnumInjuryStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumInjuryStatusWithAggregatesFilter<$PrismaModel> | $Enums.InjuryStatus
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumInjuryStatusFilter<$PrismaModel>
    _max?: NestedEnumInjuryStatusFilter<$PrismaModel>
  }

  export type EnumInjuryImpactNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.InjuryImpact | EnumInjuryImpactFieldRefInput<$PrismaModel> | null
    in?: $Enums.InjuryImpact[] | ListEnumInjuryImpactFieldRefInput<$PrismaModel> | null
    notIn?: $Enums.InjuryImpact[] | ListEnumInjuryImpactFieldRefInput<$PrismaModel> | null
    not?: NestedEnumInjuryImpactNullableWithAggregatesFilter<$PrismaModel> | $Enums.InjuryImpact | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedEnumInjuryImpactNullableFilter<$PrismaModel>
    _max?: NestedEnumInjuryImpactNullableFilter<$PrismaModel>
  }

  export type TeamProfileWeeklyTeamIdWeekStartCompoundUniqueInput = {
    teamId: string
    weekStart: Date | string
  }

  export type TeamProfileWeeklyCountOrderByAggregateInput = {
    id?: SortOrder
    teamId?: SortOrder
    weekStart?: SortOrder
    summary?: SortOrder
    tempoRank?: SortOrder
    offPpp?: SortOrder
    defPpp?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type TeamProfileWeeklyAvgOrderByAggregateInput = {
    tempoRank?: SortOrder
    offPpp?: SortOrder
    defPpp?: SortOrder
  }

  export type TeamProfileWeeklyMaxOrderByAggregateInput = {
    id?: SortOrder
    teamId?: SortOrder
    weekStart?: SortOrder
    summary?: SortOrder
    tempoRank?: SortOrder
    offPpp?: SortOrder
    defPpp?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type TeamProfileWeeklyMinOrderByAggregateInput = {
    id?: SortOrder
    teamId?: SortOrder
    weekStart?: SortOrder
    summary?: SortOrder
    tempoRank?: SortOrder
    offPpp?: SortOrder
    defPpp?: SortOrder
    createdAt?: SortOrder
    updatedAt?: SortOrder
  }

  export type TeamProfileWeeklySumOrderByAggregateInput = {
    tempoRank?: SortOrder
    offPpp?: SortOrder
    defPpp?: SortOrder
  }

  export type AccountCreateNestedManyWithoutUserInput = {
    create?: XOR<AccountCreateWithoutUserInput, AccountUncheckedCreateWithoutUserInput> | AccountCreateWithoutUserInput[] | AccountUncheckedCreateWithoutUserInput[]
    connectOrCreate?: AccountCreateOrConnectWithoutUserInput | AccountCreateOrConnectWithoutUserInput[]
    createMany?: AccountCreateManyUserInputEnvelope
    connect?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
  }

  export type SessionCreateNestedManyWithoutUserInput = {
    create?: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput> | SessionCreateWithoutUserInput[] | SessionUncheckedCreateWithoutUserInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutUserInput | SessionCreateOrConnectWithoutUserInput[]
    createMany?: SessionCreateManyUserInputEnvelope
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
  }

  export type AccountUncheckedCreateNestedManyWithoutUserInput = {
    create?: XOR<AccountCreateWithoutUserInput, AccountUncheckedCreateWithoutUserInput> | AccountCreateWithoutUserInput[] | AccountUncheckedCreateWithoutUserInput[]
    connectOrCreate?: AccountCreateOrConnectWithoutUserInput | AccountCreateOrConnectWithoutUserInput[]
    createMany?: AccountCreateManyUserInputEnvelope
    connect?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
  }

  export type SessionUncheckedCreateNestedManyWithoutUserInput = {
    create?: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput> | SessionCreateWithoutUserInput[] | SessionUncheckedCreateWithoutUserInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutUserInput | SessionCreateOrConnectWithoutUserInput[]
    createMany?: SessionCreateManyUserInputEnvelope
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
  }

  export type StringFieldUpdateOperationsInput = {
    set?: string
  }

  export type NullableDateTimeFieldUpdateOperationsInput = {
    set?: Date | string | null
  }

  export type NullableStringFieldUpdateOperationsInput = {
    set?: string | null
  }

  export type EnumUserRoleFieldUpdateOperationsInput = {
    set?: $Enums.UserRole
  }

  export type NullableEnumSubscriptionStatusFieldUpdateOperationsInput = {
    set?: $Enums.SubscriptionStatus | null
  }

  export type DateTimeFieldUpdateOperationsInput = {
    set?: Date | string
  }

  export type AccountUpdateManyWithoutUserNestedInput = {
    create?: XOR<AccountCreateWithoutUserInput, AccountUncheckedCreateWithoutUserInput> | AccountCreateWithoutUserInput[] | AccountUncheckedCreateWithoutUserInput[]
    connectOrCreate?: AccountCreateOrConnectWithoutUserInput | AccountCreateOrConnectWithoutUserInput[]
    upsert?: AccountUpsertWithWhereUniqueWithoutUserInput | AccountUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: AccountCreateManyUserInputEnvelope
    set?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
    disconnect?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
    delete?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
    connect?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
    update?: AccountUpdateWithWhereUniqueWithoutUserInput | AccountUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: AccountUpdateManyWithWhereWithoutUserInput | AccountUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: AccountScalarWhereInput | AccountScalarWhereInput[]
  }

  export type SessionUpdateManyWithoutUserNestedInput = {
    create?: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput> | SessionCreateWithoutUserInput[] | SessionUncheckedCreateWithoutUserInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutUserInput | SessionCreateOrConnectWithoutUserInput[]
    upsert?: SessionUpsertWithWhereUniqueWithoutUserInput | SessionUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: SessionCreateManyUserInputEnvelope
    set?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    disconnect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    delete?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    update?: SessionUpdateWithWhereUniqueWithoutUserInput | SessionUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: SessionUpdateManyWithWhereWithoutUserInput | SessionUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: SessionScalarWhereInput | SessionScalarWhereInput[]
  }

  export type AccountUncheckedUpdateManyWithoutUserNestedInput = {
    create?: XOR<AccountCreateWithoutUserInput, AccountUncheckedCreateWithoutUserInput> | AccountCreateWithoutUserInput[] | AccountUncheckedCreateWithoutUserInput[]
    connectOrCreate?: AccountCreateOrConnectWithoutUserInput | AccountCreateOrConnectWithoutUserInput[]
    upsert?: AccountUpsertWithWhereUniqueWithoutUserInput | AccountUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: AccountCreateManyUserInputEnvelope
    set?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
    disconnect?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
    delete?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
    connect?: AccountWhereUniqueInput | AccountWhereUniqueInput[]
    update?: AccountUpdateWithWhereUniqueWithoutUserInput | AccountUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: AccountUpdateManyWithWhereWithoutUserInput | AccountUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: AccountScalarWhereInput | AccountScalarWhereInput[]
  }

  export type SessionUncheckedUpdateManyWithoutUserNestedInput = {
    create?: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput> | SessionCreateWithoutUserInput[] | SessionUncheckedCreateWithoutUserInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutUserInput | SessionCreateOrConnectWithoutUserInput[]
    upsert?: SessionUpsertWithWhereUniqueWithoutUserInput | SessionUpsertWithWhereUniqueWithoutUserInput[]
    createMany?: SessionCreateManyUserInputEnvelope
    set?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    disconnect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    delete?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    update?: SessionUpdateWithWhereUniqueWithoutUserInput | SessionUpdateWithWhereUniqueWithoutUserInput[]
    updateMany?: SessionUpdateManyWithWhereWithoutUserInput | SessionUpdateManyWithWhereWithoutUserInput[]
    deleteMany?: SessionScalarWhereInput | SessionScalarWhereInput[]
  }

  export type UserCreateNestedOneWithoutAccountsInput = {
    create?: XOR<UserCreateWithoutAccountsInput, UserUncheckedCreateWithoutAccountsInput>
    connectOrCreate?: UserCreateOrConnectWithoutAccountsInput
    connect?: UserWhereUniqueInput
  }

  export type NullableIntFieldUpdateOperationsInput = {
    set?: number | null
    increment?: number
    decrement?: number
    multiply?: number
    divide?: number
  }

  export type UserUpdateOneRequiredWithoutAccountsNestedInput = {
    create?: XOR<UserCreateWithoutAccountsInput, UserUncheckedCreateWithoutAccountsInput>
    connectOrCreate?: UserCreateOrConnectWithoutAccountsInput
    upsert?: UserUpsertWithoutAccountsInput
    connect?: UserWhereUniqueInput
    update?: XOR<XOR<UserUpdateToOneWithWhereWithoutAccountsInput, UserUpdateWithoutAccountsInput>, UserUncheckedUpdateWithoutAccountsInput>
  }

  export type UserCreateNestedOneWithoutSessionsInput = {
    create?: XOR<UserCreateWithoutSessionsInput, UserUncheckedCreateWithoutSessionsInput>
    connectOrCreate?: UserCreateOrConnectWithoutSessionsInput
    connect?: UserWhereUniqueInput
  }

  export type UserUpdateOneRequiredWithoutSessionsNestedInput = {
    create?: XOR<UserCreateWithoutSessionsInput, UserUncheckedCreateWithoutSessionsInput>
    connectOrCreate?: UserCreateOrConnectWithoutSessionsInput
    upsert?: UserUpsertWithoutSessionsInput
    connect?: UserWhereUniqueInput
    update?: XOR<XOR<UserUpdateToOneWithWhereWithoutSessionsInput, UserUpdateWithoutSessionsInput>, UserUncheckedUpdateWithoutSessionsInput>
  }

  export type TeamCreateNestedManyWithoutSportInput = {
    create?: XOR<TeamCreateWithoutSportInput, TeamUncheckedCreateWithoutSportInput> | TeamCreateWithoutSportInput[] | TeamUncheckedCreateWithoutSportInput[]
    connectOrCreate?: TeamCreateOrConnectWithoutSportInput | TeamCreateOrConnectWithoutSportInput[]
    createMany?: TeamCreateManySportInputEnvelope
    connect?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
  }

  export type GameCreateNestedManyWithoutSportInput = {
    create?: XOR<GameCreateWithoutSportInput, GameUncheckedCreateWithoutSportInput> | GameCreateWithoutSportInput[] | GameUncheckedCreateWithoutSportInput[]
    connectOrCreate?: GameCreateOrConnectWithoutSportInput | GameCreateOrConnectWithoutSportInput[]
    createMany?: GameCreateManySportInputEnvelope
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
  }

  export type TeamUncheckedCreateNestedManyWithoutSportInput = {
    create?: XOR<TeamCreateWithoutSportInput, TeamUncheckedCreateWithoutSportInput> | TeamCreateWithoutSportInput[] | TeamUncheckedCreateWithoutSportInput[]
    connectOrCreate?: TeamCreateOrConnectWithoutSportInput | TeamCreateOrConnectWithoutSportInput[]
    createMany?: TeamCreateManySportInputEnvelope
    connect?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
  }

  export type GameUncheckedCreateNestedManyWithoutSportInput = {
    create?: XOR<GameCreateWithoutSportInput, GameUncheckedCreateWithoutSportInput> | GameCreateWithoutSportInput[] | GameUncheckedCreateWithoutSportInput[]
    connectOrCreate?: GameCreateOrConnectWithoutSportInput | GameCreateOrConnectWithoutSportInput[]
    createMany?: GameCreateManySportInputEnvelope
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
  }

  export type TeamUpdateManyWithoutSportNestedInput = {
    create?: XOR<TeamCreateWithoutSportInput, TeamUncheckedCreateWithoutSportInput> | TeamCreateWithoutSportInput[] | TeamUncheckedCreateWithoutSportInput[]
    connectOrCreate?: TeamCreateOrConnectWithoutSportInput | TeamCreateOrConnectWithoutSportInput[]
    upsert?: TeamUpsertWithWhereUniqueWithoutSportInput | TeamUpsertWithWhereUniqueWithoutSportInput[]
    createMany?: TeamCreateManySportInputEnvelope
    set?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
    disconnect?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
    delete?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
    connect?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
    update?: TeamUpdateWithWhereUniqueWithoutSportInput | TeamUpdateWithWhereUniqueWithoutSportInput[]
    updateMany?: TeamUpdateManyWithWhereWithoutSportInput | TeamUpdateManyWithWhereWithoutSportInput[]
    deleteMany?: TeamScalarWhereInput | TeamScalarWhereInput[]
  }

  export type GameUpdateManyWithoutSportNestedInput = {
    create?: XOR<GameCreateWithoutSportInput, GameUncheckedCreateWithoutSportInput> | GameCreateWithoutSportInput[] | GameUncheckedCreateWithoutSportInput[]
    connectOrCreate?: GameCreateOrConnectWithoutSportInput | GameCreateOrConnectWithoutSportInput[]
    upsert?: GameUpsertWithWhereUniqueWithoutSportInput | GameUpsertWithWhereUniqueWithoutSportInput[]
    createMany?: GameCreateManySportInputEnvelope
    set?: GameWhereUniqueInput | GameWhereUniqueInput[]
    disconnect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    delete?: GameWhereUniqueInput | GameWhereUniqueInput[]
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    update?: GameUpdateWithWhereUniqueWithoutSportInput | GameUpdateWithWhereUniqueWithoutSportInput[]
    updateMany?: GameUpdateManyWithWhereWithoutSportInput | GameUpdateManyWithWhereWithoutSportInput[]
    deleteMany?: GameScalarWhereInput | GameScalarWhereInput[]
  }

  export type TeamUncheckedUpdateManyWithoutSportNestedInput = {
    create?: XOR<TeamCreateWithoutSportInput, TeamUncheckedCreateWithoutSportInput> | TeamCreateWithoutSportInput[] | TeamUncheckedCreateWithoutSportInput[]
    connectOrCreate?: TeamCreateOrConnectWithoutSportInput | TeamCreateOrConnectWithoutSportInput[]
    upsert?: TeamUpsertWithWhereUniqueWithoutSportInput | TeamUpsertWithWhereUniqueWithoutSportInput[]
    createMany?: TeamCreateManySportInputEnvelope
    set?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
    disconnect?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
    delete?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
    connect?: TeamWhereUniqueInput | TeamWhereUniqueInput[]
    update?: TeamUpdateWithWhereUniqueWithoutSportInput | TeamUpdateWithWhereUniqueWithoutSportInput[]
    updateMany?: TeamUpdateManyWithWhereWithoutSportInput | TeamUpdateManyWithWhereWithoutSportInput[]
    deleteMany?: TeamScalarWhereInput | TeamScalarWhereInput[]
  }

  export type GameUncheckedUpdateManyWithoutSportNestedInput = {
    create?: XOR<GameCreateWithoutSportInput, GameUncheckedCreateWithoutSportInput> | GameCreateWithoutSportInput[] | GameUncheckedCreateWithoutSportInput[]
    connectOrCreate?: GameCreateOrConnectWithoutSportInput | GameCreateOrConnectWithoutSportInput[]
    upsert?: GameUpsertWithWhereUniqueWithoutSportInput | GameUpsertWithWhereUniqueWithoutSportInput[]
    createMany?: GameCreateManySportInputEnvelope
    set?: GameWhereUniqueInput | GameWhereUniqueInput[]
    disconnect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    delete?: GameWhereUniqueInput | GameWhereUniqueInput[]
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    update?: GameUpdateWithWhereUniqueWithoutSportInput | GameUpdateWithWhereUniqueWithoutSportInput[]
    updateMany?: GameUpdateManyWithWhereWithoutSportInput | GameUpdateManyWithWhereWithoutSportInput[]
    deleteMany?: GameScalarWhereInput | GameScalarWhereInput[]
  }

  export type SportCreateNestedOneWithoutTeamsInput = {
    create?: XOR<SportCreateWithoutTeamsInput, SportUncheckedCreateWithoutTeamsInput>
    connectOrCreate?: SportCreateOrConnectWithoutTeamsInput
    connect?: SportWhereUniqueInput
  }

  export type GameCreateNestedManyWithoutHomeTeamInput = {
    create?: XOR<GameCreateWithoutHomeTeamInput, GameUncheckedCreateWithoutHomeTeamInput> | GameCreateWithoutHomeTeamInput[] | GameUncheckedCreateWithoutHomeTeamInput[]
    connectOrCreate?: GameCreateOrConnectWithoutHomeTeamInput | GameCreateOrConnectWithoutHomeTeamInput[]
    createMany?: GameCreateManyHomeTeamInputEnvelope
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
  }

  export type GameCreateNestedManyWithoutAwayTeamInput = {
    create?: XOR<GameCreateWithoutAwayTeamInput, GameUncheckedCreateWithoutAwayTeamInput> | GameCreateWithoutAwayTeamInput[] | GameUncheckedCreateWithoutAwayTeamInput[]
    connectOrCreate?: GameCreateOrConnectWithoutAwayTeamInput | GameCreateOrConnectWithoutAwayTeamInput[]
    createMany?: GameCreateManyAwayTeamInputEnvelope
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
  }

  export type InjuryCreateNestedManyWithoutTeamInput = {
    create?: XOR<InjuryCreateWithoutTeamInput, InjuryUncheckedCreateWithoutTeamInput> | InjuryCreateWithoutTeamInput[] | InjuryUncheckedCreateWithoutTeamInput[]
    connectOrCreate?: InjuryCreateOrConnectWithoutTeamInput | InjuryCreateOrConnectWithoutTeamInput[]
    createMany?: InjuryCreateManyTeamInputEnvelope
    connect?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
  }

  export type TeamProfileWeeklyCreateNestedManyWithoutTeamInput = {
    create?: XOR<TeamProfileWeeklyCreateWithoutTeamInput, TeamProfileWeeklyUncheckedCreateWithoutTeamInput> | TeamProfileWeeklyCreateWithoutTeamInput[] | TeamProfileWeeklyUncheckedCreateWithoutTeamInput[]
    connectOrCreate?: TeamProfileWeeklyCreateOrConnectWithoutTeamInput | TeamProfileWeeklyCreateOrConnectWithoutTeamInput[]
    createMany?: TeamProfileWeeklyCreateManyTeamInputEnvelope
    connect?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
  }

  export type GameUncheckedCreateNestedManyWithoutHomeTeamInput = {
    create?: XOR<GameCreateWithoutHomeTeamInput, GameUncheckedCreateWithoutHomeTeamInput> | GameCreateWithoutHomeTeamInput[] | GameUncheckedCreateWithoutHomeTeamInput[]
    connectOrCreate?: GameCreateOrConnectWithoutHomeTeamInput | GameCreateOrConnectWithoutHomeTeamInput[]
    createMany?: GameCreateManyHomeTeamInputEnvelope
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
  }

  export type GameUncheckedCreateNestedManyWithoutAwayTeamInput = {
    create?: XOR<GameCreateWithoutAwayTeamInput, GameUncheckedCreateWithoutAwayTeamInput> | GameCreateWithoutAwayTeamInput[] | GameUncheckedCreateWithoutAwayTeamInput[]
    connectOrCreate?: GameCreateOrConnectWithoutAwayTeamInput | GameCreateOrConnectWithoutAwayTeamInput[]
    createMany?: GameCreateManyAwayTeamInputEnvelope
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
  }

  export type InjuryUncheckedCreateNestedManyWithoutTeamInput = {
    create?: XOR<InjuryCreateWithoutTeamInput, InjuryUncheckedCreateWithoutTeamInput> | InjuryCreateWithoutTeamInput[] | InjuryUncheckedCreateWithoutTeamInput[]
    connectOrCreate?: InjuryCreateOrConnectWithoutTeamInput | InjuryCreateOrConnectWithoutTeamInput[]
    createMany?: InjuryCreateManyTeamInputEnvelope
    connect?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
  }

  export type TeamProfileWeeklyUncheckedCreateNestedManyWithoutTeamInput = {
    create?: XOR<TeamProfileWeeklyCreateWithoutTeamInput, TeamProfileWeeklyUncheckedCreateWithoutTeamInput> | TeamProfileWeeklyCreateWithoutTeamInput[] | TeamProfileWeeklyUncheckedCreateWithoutTeamInput[]
    connectOrCreate?: TeamProfileWeeklyCreateOrConnectWithoutTeamInput | TeamProfileWeeklyCreateOrConnectWithoutTeamInput[]
    createMany?: TeamProfileWeeklyCreateManyTeamInputEnvelope
    connect?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
  }

  export type SportUpdateOneRequiredWithoutTeamsNestedInput = {
    create?: XOR<SportCreateWithoutTeamsInput, SportUncheckedCreateWithoutTeamsInput>
    connectOrCreate?: SportCreateOrConnectWithoutTeamsInput
    upsert?: SportUpsertWithoutTeamsInput
    connect?: SportWhereUniqueInput
    update?: XOR<XOR<SportUpdateToOneWithWhereWithoutTeamsInput, SportUpdateWithoutTeamsInput>, SportUncheckedUpdateWithoutTeamsInput>
  }

  export type GameUpdateManyWithoutHomeTeamNestedInput = {
    create?: XOR<GameCreateWithoutHomeTeamInput, GameUncheckedCreateWithoutHomeTeamInput> | GameCreateWithoutHomeTeamInput[] | GameUncheckedCreateWithoutHomeTeamInput[]
    connectOrCreate?: GameCreateOrConnectWithoutHomeTeamInput | GameCreateOrConnectWithoutHomeTeamInput[]
    upsert?: GameUpsertWithWhereUniqueWithoutHomeTeamInput | GameUpsertWithWhereUniqueWithoutHomeTeamInput[]
    createMany?: GameCreateManyHomeTeamInputEnvelope
    set?: GameWhereUniqueInput | GameWhereUniqueInput[]
    disconnect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    delete?: GameWhereUniqueInput | GameWhereUniqueInput[]
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    update?: GameUpdateWithWhereUniqueWithoutHomeTeamInput | GameUpdateWithWhereUniqueWithoutHomeTeamInput[]
    updateMany?: GameUpdateManyWithWhereWithoutHomeTeamInput | GameUpdateManyWithWhereWithoutHomeTeamInput[]
    deleteMany?: GameScalarWhereInput | GameScalarWhereInput[]
  }

  export type GameUpdateManyWithoutAwayTeamNestedInput = {
    create?: XOR<GameCreateWithoutAwayTeamInput, GameUncheckedCreateWithoutAwayTeamInput> | GameCreateWithoutAwayTeamInput[] | GameUncheckedCreateWithoutAwayTeamInput[]
    connectOrCreate?: GameCreateOrConnectWithoutAwayTeamInput | GameCreateOrConnectWithoutAwayTeamInput[]
    upsert?: GameUpsertWithWhereUniqueWithoutAwayTeamInput | GameUpsertWithWhereUniqueWithoutAwayTeamInput[]
    createMany?: GameCreateManyAwayTeamInputEnvelope
    set?: GameWhereUniqueInput | GameWhereUniqueInput[]
    disconnect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    delete?: GameWhereUniqueInput | GameWhereUniqueInput[]
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    update?: GameUpdateWithWhereUniqueWithoutAwayTeamInput | GameUpdateWithWhereUniqueWithoutAwayTeamInput[]
    updateMany?: GameUpdateManyWithWhereWithoutAwayTeamInput | GameUpdateManyWithWhereWithoutAwayTeamInput[]
    deleteMany?: GameScalarWhereInput | GameScalarWhereInput[]
  }

  export type InjuryUpdateManyWithoutTeamNestedInput = {
    create?: XOR<InjuryCreateWithoutTeamInput, InjuryUncheckedCreateWithoutTeamInput> | InjuryCreateWithoutTeamInput[] | InjuryUncheckedCreateWithoutTeamInput[]
    connectOrCreate?: InjuryCreateOrConnectWithoutTeamInput | InjuryCreateOrConnectWithoutTeamInput[]
    upsert?: InjuryUpsertWithWhereUniqueWithoutTeamInput | InjuryUpsertWithWhereUniqueWithoutTeamInput[]
    createMany?: InjuryCreateManyTeamInputEnvelope
    set?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
    disconnect?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
    delete?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
    connect?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
    update?: InjuryUpdateWithWhereUniqueWithoutTeamInput | InjuryUpdateWithWhereUniqueWithoutTeamInput[]
    updateMany?: InjuryUpdateManyWithWhereWithoutTeamInput | InjuryUpdateManyWithWhereWithoutTeamInput[]
    deleteMany?: InjuryScalarWhereInput | InjuryScalarWhereInput[]
  }

  export type TeamProfileWeeklyUpdateManyWithoutTeamNestedInput = {
    create?: XOR<TeamProfileWeeklyCreateWithoutTeamInput, TeamProfileWeeklyUncheckedCreateWithoutTeamInput> | TeamProfileWeeklyCreateWithoutTeamInput[] | TeamProfileWeeklyUncheckedCreateWithoutTeamInput[]
    connectOrCreate?: TeamProfileWeeklyCreateOrConnectWithoutTeamInput | TeamProfileWeeklyCreateOrConnectWithoutTeamInput[]
    upsert?: TeamProfileWeeklyUpsertWithWhereUniqueWithoutTeamInput | TeamProfileWeeklyUpsertWithWhereUniqueWithoutTeamInput[]
    createMany?: TeamProfileWeeklyCreateManyTeamInputEnvelope
    set?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
    disconnect?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
    delete?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
    connect?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
    update?: TeamProfileWeeklyUpdateWithWhereUniqueWithoutTeamInput | TeamProfileWeeklyUpdateWithWhereUniqueWithoutTeamInput[]
    updateMany?: TeamProfileWeeklyUpdateManyWithWhereWithoutTeamInput | TeamProfileWeeklyUpdateManyWithWhereWithoutTeamInput[]
    deleteMany?: TeamProfileWeeklyScalarWhereInput | TeamProfileWeeklyScalarWhereInput[]
  }

  export type GameUncheckedUpdateManyWithoutHomeTeamNestedInput = {
    create?: XOR<GameCreateWithoutHomeTeamInput, GameUncheckedCreateWithoutHomeTeamInput> | GameCreateWithoutHomeTeamInput[] | GameUncheckedCreateWithoutHomeTeamInput[]
    connectOrCreate?: GameCreateOrConnectWithoutHomeTeamInput | GameCreateOrConnectWithoutHomeTeamInput[]
    upsert?: GameUpsertWithWhereUniqueWithoutHomeTeamInput | GameUpsertWithWhereUniqueWithoutHomeTeamInput[]
    createMany?: GameCreateManyHomeTeamInputEnvelope
    set?: GameWhereUniqueInput | GameWhereUniqueInput[]
    disconnect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    delete?: GameWhereUniqueInput | GameWhereUniqueInput[]
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    update?: GameUpdateWithWhereUniqueWithoutHomeTeamInput | GameUpdateWithWhereUniqueWithoutHomeTeamInput[]
    updateMany?: GameUpdateManyWithWhereWithoutHomeTeamInput | GameUpdateManyWithWhereWithoutHomeTeamInput[]
    deleteMany?: GameScalarWhereInput | GameScalarWhereInput[]
  }

  export type GameUncheckedUpdateManyWithoutAwayTeamNestedInput = {
    create?: XOR<GameCreateWithoutAwayTeamInput, GameUncheckedCreateWithoutAwayTeamInput> | GameCreateWithoutAwayTeamInput[] | GameUncheckedCreateWithoutAwayTeamInput[]
    connectOrCreate?: GameCreateOrConnectWithoutAwayTeamInput | GameCreateOrConnectWithoutAwayTeamInput[]
    upsert?: GameUpsertWithWhereUniqueWithoutAwayTeamInput | GameUpsertWithWhereUniqueWithoutAwayTeamInput[]
    createMany?: GameCreateManyAwayTeamInputEnvelope
    set?: GameWhereUniqueInput | GameWhereUniqueInput[]
    disconnect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    delete?: GameWhereUniqueInput | GameWhereUniqueInput[]
    connect?: GameWhereUniqueInput | GameWhereUniqueInput[]
    update?: GameUpdateWithWhereUniqueWithoutAwayTeamInput | GameUpdateWithWhereUniqueWithoutAwayTeamInput[]
    updateMany?: GameUpdateManyWithWhereWithoutAwayTeamInput | GameUpdateManyWithWhereWithoutAwayTeamInput[]
    deleteMany?: GameScalarWhereInput | GameScalarWhereInput[]
  }

  export type InjuryUncheckedUpdateManyWithoutTeamNestedInput = {
    create?: XOR<InjuryCreateWithoutTeamInput, InjuryUncheckedCreateWithoutTeamInput> | InjuryCreateWithoutTeamInput[] | InjuryUncheckedCreateWithoutTeamInput[]
    connectOrCreate?: InjuryCreateOrConnectWithoutTeamInput | InjuryCreateOrConnectWithoutTeamInput[]
    upsert?: InjuryUpsertWithWhereUniqueWithoutTeamInput | InjuryUpsertWithWhereUniqueWithoutTeamInput[]
    createMany?: InjuryCreateManyTeamInputEnvelope
    set?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
    disconnect?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
    delete?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
    connect?: InjuryWhereUniqueInput | InjuryWhereUniqueInput[]
    update?: InjuryUpdateWithWhereUniqueWithoutTeamInput | InjuryUpdateWithWhereUniqueWithoutTeamInput[]
    updateMany?: InjuryUpdateManyWithWhereWithoutTeamInput | InjuryUpdateManyWithWhereWithoutTeamInput[]
    deleteMany?: InjuryScalarWhereInput | InjuryScalarWhereInput[]
  }

  export type TeamProfileWeeklyUncheckedUpdateManyWithoutTeamNestedInput = {
    create?: XOR<TeamProfileWeeklyCreateWithoutTeamInput, TeamProfileWeeklyUncheckedCreateWithoutTeamInput> | TeamProfileWeeklyCreateWithoutTeamInput[] | TeamProfileWeeklyUncheckedCreateWithoutTeamInput[]
    connectOrCreate?: TeamProfileWeeklyCreateOrConnectWithoutTeamInput | TeamProfileWeeklyCreateOrConnectWithoutTeamInput[]
    upsert?: TeamProfileWeeklyUpsertWithWhereUniqueWithoutTeamInput | TeamProfileWeeklyUpsertWithWhereUniqueWithoutTeamInput[]
    createMany?: TeamProfileWeeklyCreateManyTeamInputEnvelope
    set?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
    disconnect?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
    delete?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
    connect?: TeamProfileWeeklyWhereUniqueInput | TeamProfileWeeklyWhereUniqueInput[]
    update?: TeamProfileWeeklyUpdateWithWhereUniqueWithoutTeamInput | TeamProfileWeeklyUpdateWithWhereUniqueWithoutTeamInput[]
    updateMany?: TeamProfileWeeklyUpdateManyWithWhereWithoutTeamInput | TeamProfileWeeklyUpdateManyWithWhereWithoutTeamInput[]
    deleteMany?: TeamProfileWeeklyScalarWhereInput | TeamProfileWeeklyScalarWhereInput[]
  }

  export type SportCreateNestedOneWithoutGamesInput = {
    create?: XOR<SportCreateWithoutGamesInput, SportUncheckedCreateWithoutGamesInput>
    connectOrCreate?: SportCreateOrConnectWithoutGamesInput
    connect?: SportWhereUniqueInput
  }

  export type TeamCreateNestedOneWithoutHomeGamesInput = {
    create?: XOR<TeamCreateWithoutHomeGamesInput, TeamUncheckedCreateWithoutHomeGamesInput>
    connectOrCreate?: TeamCreateOrConnectWithoutHomeGamesInput
    connect?: TeamWhereUniqueInput
  }

  export type TeamCreateNestedOneWithoutAwayGamesInput = {
    create?: XOR<TeamCreateWithoutAwayGamesInput, TeamUncheckedCreateWithoutAwayGamesInput>
    connectOrCreate?: TeamCreateOrConnectWithoutAwayGamesInput
    connect?: TeamWhereUniqueInput
  }

  export type MarketSnapshotCreateNestedOneWithoutGameInput = {
    create?: XOR<MarketSnapshotCreateWithoutGameInput, MarketSnapshotUncheckedCreateWithoutGameInput>
    connectOrCreate?: MarketSnapshotCreateOrConnectWithoutGameInput
    connect?: MarketSnapshotWhereUniqueInput
  }

  export type ModelProjectionCreateNestedOneWithoutGameInput = {
    create?: XOR<ModelProjectionCreateWithoutGameInput, ModelProjectionUncheckedCreateWithoutGameInput>
    connectOrCreate?: ModelProjectionCreateOrConnectWithoutGameInput
    connect?: ModelProjectionWhereUniqueInput
  }

  export type WriteupCreateNestedOneWithoutGameInput = {
    create?: XOR<WriteupCreateWithoutGameInput, WriteupUncheckedCreateWithoutGameInput>
    connectOrCreate?: WriteupCreateOrConnectWithoutGameInput
    connect?: WriteupWhereUniqueInput
  }

  export type MarketSnapshotUncheckedCreateNestedOneWithoutGameInput = {
    create?: XOR<MarketSnapshotCreateWithoutGameInput, MarketSnapshotUncheckedCreateWithoutGameInput>
    connectOrCreate?: MarketSnapshotCreateOrConnectWithoutGameInput
    connect?: MarketSnapshotWhereUniqueInput
  }

  export type ModelProjectionUncheckedCreateNestedOneWithoutGameInput = {
    create?: XOR<ModelProjectionCreateWithoutGameInput, ModelProjectionUncheckedCreateWithoutGameInput>
    connectOrCreate?: ModelProjectionCreateOrConnectWithoutGameInput
    connect?: ModelProjectionWhereUniqueInput
  }

  export type WriteupUncheckedCreateNestedOneWithoutGameInput = {
    create?: XOR<WriteupCreateWithoutGameInput, WriteupUncheckedCreateWithoutGameInput>
    connectOrCreate?: WriteupCreateOrConnectWithoutGameInput
    connect?: WriteupWhereUniqueInput
  }

  export type SportUpdateOneRequiredWithoutGamesNestedInput = {
    create?: XOR<SportCreateWithoutGamesInput, SportUncheckedCreateWithoutGamesInput>
    connectOrCreate?: SportCreateOrConnectWithoutGamesInput
    upsert?: SportUpsertWithoutGamesInput
    connect?: SportWhereUniqueInput
    update?: XOR<XOR<SportUpdateToOneWithWhereWithoutGamesInput, SportUpdateWithoutGamesInput>, SportUncheckedUpdateWithoutGamesInput>
  }

  export type TeamUpdateOneRequiredWithoutHomeGamesNestedInput = {
    create?: XOR<TeamCreateWithoutHomeGamesInput, TeamUncheckedCreateWithoutHomeGamesInput>
    connectOrCreate?: TeamCreateOrConnectWithoutHomeGamesInput
    upsert?: TeamUpsertWithoutHomeGamesInput
    connect?: TeamWhereUniqueInput
    update?: XOR<XOR<TeamUpdateToOneWithWhereWithoutHomeGamesInput, TeamUpdateWithoutHomeGamesInput>, TeamUncheckedUpdateWithoutHomeGamesInput>
  }

  export type TeamUpdateOneRequiredWithoutAwayGamesNestedInput = {
    create?: XOR<TeamCreateWithoutAwayGamesInput, TeamUncheckedCreateWithoutAwayGamesInput>
    connectOrCreate?: TeamCreateOrConnectWithoutAwayGamesInput
    upsert?: TeamUpsertWithoutAwayGamesInput
    connect?: TeamWhereUniqueInput
    update?: XOR<XOR<TeamUpdateToOneWithWhereWithoutAwayGamesInput, TeamUpdateWithoutAwayGamesInput>, TeamUncheckedUpdateWithoutAwayGamesInput>
  }

  export type MarketSnapshotUpdateOneWithoutGameNestedInput = {
    create?: XOR<MarketSnapshotCreateWithoutGameInput, MarketSnapshotUncheckedCreateWithoutGameInput>
    connectOrCreate?: MarketSnapshotCreateOrConnectWithoutGameInput
    upsert?: MarketSnapshotUpsertWithoutGameInput
    disconnect?: MarketSnapshotWhereInput | boolean
    delete?: MarketSnapshotWhereInput | boolean
    connect?: MarketSnapshotWhereUniqueInput
    update?: XOR<XOR<MarketSnapshotUpdateToOneWithWhereWithoutGameInput, MarketSnapshotUpdateWithoutGameInput>, MarketSnapshotUncheckedUpdateWithoutGameInput>
  }

  export type ModelProjectionUpdateOneWithoutGameNestedInput = {
    create?: XOR<ModelProjectionCreateWithoutGameInput, ModelProjectionUncheckedCreateWithoutGameInput>
    connectOrCreate?: ModelProjectionCreateOrConnectWithoutGameInput
    upsert?: ModelProjectionUpsertWithoutGameInput
    disconnect?: ModelProjectionWhereInput | boolean
    delete?: ModelProjectionWhereInput | boolean
    connect?: ModelProjectionWhereUniqueInput
    update?: XOR<XOR<ModelProjectionUpdateToOneWithWhereWithoutGameInput, ModelProjectionUpdateWithoutGameInput>, ModelProjectionUncheckedUpdateWithoutGameInput>
  }

  export type WriteupUpdateOneWithoutGameNestedInput = {
    create?: XOR<WriteupCreateWithoutGameInput, WriteupUncheckedCreateWithoutGameInput>
    connectOrCreate?: WriteupCreateOrConnectWithoutGameInput
    upsert?: WriteupUpsertWithoutGameInput
    disconnect?: WriteupWhereInput | boolean
    delete?: WriteupWhereInput | boolean
    connect?: WriteupWhereUniqueInput
    update?: XOR<XOR<WriteupUpdateToOneWithWhereWithoutGameInput, WriteupUpdateWithoutGameInput>, WriteupUncheckedUpdateWithoutGameInput>
  }

  export type MarketSnapshotUncheckedUpdateOneWithoutGameNestedInput = {
    create?: XOR<MarketSnapshotCreateWithoutGameInput, MarketSnapshotUncheckedCreateWithoutGameInput>
    connectOrCreate?: MarketSnapshotCreateOrConnectWithoutGameInput
    upsert?: MarketSnapshotUpsertWithoutGameInput
    disconnect?: MarketSnapshotWhereInput | boolean
    delete?: MarketSnapshotWhereInput | boolean
    connect?: MarketSnapshotWhereUniqueInput
    update?: XOR<XOR<MarketSnapshotUpdateToOneWithWhereWithoutGameInput, MarketSnapshotUpdateWithoutGameInput>, MarketSnapshotUncheckedUpdateWithoutGameInput>
  }

  export type ModelProjectionUncheckedUpdateOneWithoutGameNestedInput = {
    create?: XOR<ModelProjectionCreateWithoutGameInput, ModelProjectionUncheckedCreateWithoutGameInput>
    connectOrCreate?: ModelProjectionCreateOrConnectWithoutGameInput
    upsert?: ModelProjectionUpsertWithoutGameInput
    disconnect?: ModelProjectionWhereInput | boolean
    delete?: ModelProjectionWhereInput | boolean
    connect?: ModelProjectionWhereUniqueInput
    update?: XOR<XOR<ModelProjectionUpdateToOneWithWhereWithoutGameInput, ModelProjectionUpdateWithoutGameInput>, ModelProjectionUncheckedUpdateWithoutGameInput>
  }

  export type WriteupUncheckedUpdateOneWithoutGameNestedInput = {
    create?: XOR<WriteupCreateWithoutGameInput, WriteupUncheckedCreateWithoutGameInput>
    connectOrCreate?: WriteupCreateOrConnectWithoutGameInput
    upsert?: WriteupUpsertWithoutGameInput
    disconnect?: WriteupWhereInput | boolean
    delete?: WriteupWhereInput | boolean
    connect?: WriteupWhereUniqueInput
    update?: XOR<XOR<WriteupUpdateToOneWithWhereWithoutGameInput, WriteupUpdateWithoutGameInput>, WriteupUncheckedUpdateWithoutGameInput>
  }

  export type BookLineCreateNestedManyWithoutMarketInput = {
    create?: XOR<BookLineCreateWithoutMarketInput, BookLineUncheckedCreateWithoutMarketInput> | BookLineCreateWithoutMarketInput[] | BookLineUncheckedCreateWithoutMarketInput[]
    connectOrCreate?: BookLineCreateOrConnectWithoutMarketInput | BookLineCreateOrConnectWithoutMarketInput[]
    createMany?: BookLineCreateManyMarketInputEnvelope
    connect?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
  }

  export type GameCreateNestedOneWithoutMarketInput = {
    create?: XOR<GameCreateWithoutMarketInput, GameUncheckedCreateWithoutMarketInput>
    connectOrCreate?: GameCreateOrConnectWithoutMarketInput
    connect?: GameWhereUniqueInput
  }

  export type BookLineUncheckedCreateNestedManyWithoutMarketInput = {
    create?: XOR<BookLineCreateWithoutMarketInput, BookLineUncheckedCreateWithoutMarketInput> | BookLineCreateWithoutMarketInput[] | BookLineUncheckedCreateWithoutMarketInput[]
    connectOrCreate?: BookLineCreateOrConnectWithoutMarketInput | BookLineCreateOrConnectWithoutMarketInput[]
    createMany?: BookLineCreateManyMarketInputEnvelope
    connect?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
  }

  export type NullableFloatFieldUpdateOperationsInput = {
    set?: number | null
    increment?: number
    decrement?: number
    multiply?: number
    divide?: number
  }

  export type BookLineUpdateManyWithoutMarketNestedInput = {
    create?: XOR<BookLineCreateWithoutMarketInput, BookLineUncheckedCreateWithoutMarketInput> | BookLineCreateWithoutMarketInput[] | BookLineUncheckedCreateWithoutMarketInput[]
    connectOrCreate?: BookLineCreateOrConnectWithoutMarketInput | BookLineCreateOrConnectWithoutMarketInput[]
    upsert?: BookLineUpsertWithWhereUniqueWithoutMarketInput | BookLineUpsertWithWhereUniqueWithoutMarketInput[]
    createMany?: BookLineCreateManyMarketInputEnvelope
    set?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
    disconnect?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
    delete?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
    connect?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
    update?: BookLineUpdateWithWhereUniqueWithoutMarketInput | BookLineUpdateWithWhereUniqueWithoutMarketInput[]
    updateMany?: BookLineUpdateManyWithWhereWithoutMarketInput | BookLineUpdateManyWithWhereWithoutMarketInput[]
    deleteMany?: BookLineScalarWhereInput | BookLineScalarWhereInput[]
  }

  export type GameUpdateOneRequiredWithoutMarketNestedInput = {
    create?: XOR<GameCreateWithoutMarketInput, GameUncheckedCreateWithoutMarketInput>
    connectOrCreate?: GameCreateOrConnectWithoutMarketInput
    upsert?: GameUpsertWithoutMarketInput
    connect?: GameWhereUniqueInput
    update?: XOR<XOR<GameUpdateToOneWithWhereWithoutMarketInput, GameUpdateWithoutMarketInput>, GameUncheckedUpdateWithoutMarketInput>
  }

  export type BookLineUncheckedUpdateManyWithoutMarketNestedInput = {
    create?: XOR<BookLineCreateWithoutMarketInput, BookLineUncheckedCreateWithoutMarketInput> | BookLineCreateWithoutMarketInput[] | BookLineUncheckedCreateWithoutMarketInput[]
    connectOrCreate?: BookLineCreateOrConnectWithoutMarketInput | BookLineCreateOrConnectWithoutMarketInput[]
    upsert?: BookLineUpsertWithWhereUniqueWithoutMarketInput | BookLineUpsertWithWhereUniqueWithoutMarketInput[]
    createMany?: BookLineCreateManyMarketInputEnvelope
    set?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
    disconnect?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
    delete?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
    connect?: BookLineWhereUniqueInput | BookLineWhereUniqueInput[]
    update?: BookLineUpdateWithWhereUniqueWithoutMarketInput | BookLineUpdateWithWhereUniqueWithoutMarketInput[]
    updateMany?: BookLineUpdateManyWithWhereWithoutMarketInput | BookLineUpdateManyWithWhereWithoutMarketInput[]
    deleteMany?: BookLineScalarWhereInput | BookLineScalarWhereInput[]
  }

  export type MarketSnapshotCreateNestedOneWithoutBookLinesInput = {
    create?: XOR<MarketSnapshotCreateWithoutBookLinesInput, MarketSnapshotUncheckedCreateWithoutBookLinesInput>
    connectOrCreate?: MarketSnapshotCreateOrConnectWithoutBookLinesInput
    connect?: MarketSnapshotWhereUniqueInput
  }

  export type MarketSnapshotUpdateOneRequiredWithoutBookLinesNestedInput = {
    create?: XOR<MarketSnapshotCreateWithoutBookLinesInput, MarketSnapshotUncheckedCreateWithoutBookLinesInput>
    connectOrCreate?: MarketSnapshotCreateOrConnectWithoutBookLinesInput
    upsert?: MarketSnapshotUpsertWithoutBookLinesInput
    connect?: MarketSnapshotWhereUniqueInput
    update?: XOR<XOR<MarketSnapshotUpdateToOneWithWhereWithoutBookLinesInput, MarketSnapshotUpdateWithoutBookLinesInput>, MarketSnapshotUncheckedUpdateWithoutBookLinesInput>
  }

  export type GameCreateNestedOneWithoutModelInput = {
    create?: XOR<GameCreateWithoutModelInput, GameUncheckedCreateWithoutModelInput>
    connectOrCreate?: GameCreateOrConnectWithoutModelInput
    connect?: GameWhereUniqueInput
  }

  export type FloatFieldUpdateOperationsInput = {
    set?: number
    increment?: number
    decrement?: number
    multiply?: number
    divide?: number
  }

  export type GameUpdateOneRequiredWithoutModelNestedInput = {
    create?: XOR<GameCreateWithoutModelInput, GameUncheckedCreateWithoutModelInput>
    connectOrCreate?: GameCreateOrConnectWithoutModelInput
    upsert?: GameUpsertWithoutModelInput
    connect?: GameWhereUniqueInput
    update?: XOR<XOR<GameUpdateToOneWithWhereWithoutModelInput, GameUpdateWithoutModelInput>, GameUncheckedUpdateWithoutModelInput>
  }

  export type GameCreateNestedOneWithoutWriteupInput = {
    create?: XOR<GameCreateWithoutWriteupInput, GameUncheckedCreateWithoutWriteupInput>
    connectOrCreate?: GameCreateOrConnectWithoutWriteupInput
    connect?: GameWhereUniqueInput
  }

  export type BoolFieldUpdateOperationsInput = {
    set?: boolean
  }

  export type EnumEditorStatusFieldUpdateOperationsInput = {
    set?: $Enums.EditorStatus
  }

  export type GameUpdateOneRequiredWithoutWriteupNestedInput = {
    create?: XOR<GameCreateWithoutWriteupInput, GameUncheckedCreateWithoutWriteupInput>
    connectOrCreate?: GameCreateOrConnectWithoutWriteupInput
    upsert?: GameUpsertWithoutWriteupInput
    connect?: GameWhereUniqueInput
    update?: XOR<XOR<GameUpdateToOneWithWhereWithoutWriteupInput, GameUpdateWithoutWriteupInput>, GameUncheckedUpdateWithoutWriteupInput>
  }

  export type TeamCreateNestedOneWithoutInjuriesInput = {
    create?: XOR<TeamCreateWithoutInjuriesInput, TeamUncheckedCreateWithoutInjuriesInput>
    connectOrCreate?: TeamCreateOrConnectWithoutInjuriesInput
    connect?: TeamWhereUniqueInput
  }

  export type EnumInjuryStatusFieldUpdateOperationsInput = {
    set?: $Enums.InjuryStatus
  }

  export type NullableEnumInjuryImpactFieldUpdateOperationsInput = {
    set?: $Enums.InjuryImpact | null
  }

  export type TeamUpdateOneRequiredWithoutInjuriesNestedInput = {
    create?: XOR<TeamCreateWithoutInjuriesInput, TeamUncheckedCreateWithoutInjuriesInput>
    connectOrCreate?: TeamCreateOrConnectWithoutInjuriesInput
    upsert?: TeamUpsertWithoutInjuriesInput
    connect?: TeamWhereUniqueInput
    update?: XOR<XOR<TeamUpdateToOneWithWhereWithoutInjuriesInput, TeamUpdateWithoutInjuriesInput>, TeamUncheckedUpdateWithoutInjuriesInput>
  }

  export type TeamCreateNestedOneWithoutProfilesInput = {
    create?: XOR<TeamCreateWithoutProfilesInput, TeamUncheckedCreateWithoutProfilesInput>
    connectOrCreate?: TeamCreateOrConnectWithoutProfilesInput
    connect?: TeamWhereUniqueInput
  }

  export type TeamUpdateOneRequiredWithoutProfilesNestedInput = {
    create?: XOR<TeamCreateWithoutProfilesInput, TeamUncheckedCreateWithoutProfilesInput>
    connectOrCreate?: TeamCreateOrConnectWithoutProfilesInput
    upsert?: TeamUpsertWithoutProfilesInput
    connect?: TeamWhereUniqueInput
    update?: XOR<XOR<TeamUpdateToOneWithWhereWithoutProfilesInput, TeamUpdateWithoutProfilesInput>, TeamUncheckedUpdateWithoutProfilesInput>
  }

  export type NestedStringFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringFilter<$PrismaModel> | string
  }

  export type NestedDateTimeNullableFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableFilter<$PrismaModel> | Date | string | null
  }

  export type NestedStringNullableFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringNullableFilter<$PrismaModel> | string | null
  }

  export type NestedEnumUserRoleFilter<$PrismaModel = never> = {
    equals?: $Enums.UserRole | EnumUserRoleFieldRefInput<$PrismaModel>
    in?: $Enums.UserRole[] | ListEnumUserRoleFieldRefInput<$PrismaModel>
    notIn?: $Enums.UserRole[] | ListEnumUserRoleFieldRefInput<$PrismaModel>
    not?: NestedEnumUserRoleFilter<$PrismaModel> | $Enums.UserRole
  }

  export type NestedEnumSubscriptionStatusNullableFilter<$PrismaModel = never> = {
    equals?: $Enums.SubscriptionStatus | EnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    in?: $Enums.SubscriptionStatus[] | ListEnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    notIn?: $Enums.SubscriptionStatus[] | ListEnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    not?: NestedEnumSubscriptionStatusNullableFilter<$PrismaModel> | $Enums.SubscriptionStatus | null
  }

  export type NestedDateTimeFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeFilter<$PrismaModel> | Date | string
  }

  export type NestedStringWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringWithAggregatesFilter<$PrismaModel> | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedStringFilter<$PrismaModel>
    _max?: NestedStringFilter<$PrismaModel>
  }

  export type NestedIntFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel>
    in?: number[] | ListIntFieldRefInput<$PrismaModel>
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel>
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntFilter<$PrismaModel> | number
  }

  export type NestedDateTimeNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableWithAggregatesFilter<$PrismaModel> | Date | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedDateTimeNullableFilter<$PrismaModel>
    _max?: NestedDateTimeNullableFilter<$PrismaModel>
  }

  export type NestedIntNullableFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel> | null
    in?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntNullableFilter<$PrismaModel> | number | null
  }

  export type NestedStringNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringNullableWithAggregatesFilter<$PrismaModel> | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedStringNullableFilter<$PrismaModel>
    _max?: NestedStringNullableFilter<$PrismaModel>
  }

  export type NestedEnumUserRoleWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.UserRole | EnumUserRoleFieldRefInput<$PrismaModel>
    in?: $Enums.UserRole[] | ListEnumUserRoleFieldRefInput<$PrismaModel>
    notIn?: $Enums.UserRole[] | ListEnumUserRoleFieldRefInput<$PrismaModel>
    not?: NestedEnumUserRoleWithAggregatesFilter<$PrismaModel> | $Enums.UserRole
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumUserRoleFilter<$PrismaModel>
    _max?: NestedEnumUserRoleFilter<$PrismaModel>
  }

  export type NestedEnumSubscriptionStatusNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.SubscriptionStatus | EnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    in?: $Enums.SubscriptionStatus[] | ListEnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    notIn?: $Enums.SubscriptionStatus[] | ListEnumSubscriptionStatusFieldRefInput<$PrismaModel> | null
    not?: NestedEnumSubscriptionStatusNullableWithAggregatesFilter<$PrismaModel> | $Enums.SubscriptionStatus | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedEnumSubscriptionStatusNullableFilter<$PrismaModel>
    _max?: NestedEnumSubscriptionStatusNullableFilter<$PrismaModel>
  }

  export type NestedDateTimeWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeWithAggregatesFilter<$PrismaModel> | Date | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedDateTimeFilter<$PrismaModel>
    _max?: NestedDateTimeFilter<$PrismaModel>
  }

  export type NestedIntNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel> | null
    in?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntNullableWithAggregatesFilter<$PrismaModel> | number | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _avg?: NestedFloatNullableFilter<$PrismaModel>
    _sum?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedIntNullableFilter<$PrismaModel>
    _max?: NestedIntNullableFilter<$PrismaModel>
  }

  export type NestedFloatNullableFilter<$PrismaModel = never> = {
    equals?: number | FloatFieldRefInput<$PrismaModel> | null
    in?: number[] | ListFloatFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListFloatFieldRefInput<$PrismaModel> | null
    lt?: number | FloatFieldRefInput<$PrismaModel>
    lte?: number | FloatFieldRefInput<$PrismaModel>
    gt?: number | FloatFieldRefInput<$PrismaModel>
    gte?: number | FloatFieldRefInput<$PrismaModel>
    not?: NestedFloatNullableFilter<$PrismaModel> | number | null
  }

  export type NestedFloatNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: number | FloatFieldRefInput<$PrismaModel> | null
    in?: number[] | ListFloatFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListFloatFieldRefInput<$PrismaModel> | null
    lt?: number | FloatFieldRefInput<$PrismaModel>
    lte?: number | FloatFieldRefInput<$PrismaModel>
    gt?: number | FloatFieldRefInput<$PrismaModel>
    gte?: number | FloatFieldRefInput<$PrismaModel>
    not?: NestedFloatNullableWithAggregatesFilter<$PrismaModel> | number | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _avg?: NestedFloatNullableFilter<$PrismaModel>
    _sum?: NestedFloatNullableFilter<$PrismaModel>
    _min?: NestedFloatNullableFilter<$PrismaModel>
    _max?: NestedFloatNullableFilter<$PrismaModel>
  }

  export type NestedFloatFilter<$PrismaModel = never> = {
    equals?: number | FloatFieldRefInput<$PrismaModel>
    in?: number[] | ListFloatFieldRefInput<$PrismaModel>
    notIn?: number[] | ListFloatFieldRefInput<$PrismaModel>
    lt?: number | FloatFieldRefInput<$PrismaModel>
    lte?: number | FloatFieldRefInput<$PrismaModel>
    gt?: number | FloatFieldRefInput<$PrismaModel>
    gte?: number | FloatFieldRefInput<$PrismaModel>
    not?: NestedFloatFilter<$PrismaModel> | number
  }

  export type NestedFloatWithAggregatesFilter<$PrismaModel = never> = {
    equals?: number | FloatFieldRefInput<$PrismaModel>
    in?: number[] | ListFloatFieldRefInput<$PrismaModel>
    notIn?: number[] | ListFloatFieldRefInput<$PrismaModel>
    lt?: number | FloatFieldRefInput<$PrismaModel>
    lte?: number | FloatFieldRefInput<$PrismaModel>
    gt?: number | FloatFieldRefInput<$PrismaModel>
    gte?: number | FloatFieldRefInput<$PrismaModel>
    not?: NestedFloatWithAggregatesFilter<$PrismaModel> | number
    _count?: NestedIntFilter<$PrismaModel>
    _avg?: NestedFloatFilter<$PrismaModel>
    _sum?: NestedFloatFilter<$PrismaModel>
    _min?: NestedFloatFilter<$PrismaModel>
    _max?: NestedFloatFilter<$PrismaModel>
  }

  export type NestedBoolFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolFilter<$PrismaModel> | boolean
  }

  export type NestedEnumEditorStatusFilter<$PrismaModel = never> = {
    equals?: $Enums.EditorStatus | EnumEditorStatusFieldRefInput<$PrismaModel>
    in?: $Enums.EditorStatus[] | ListEnumEditorStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.EditorStatus[] | ListEnumEditorStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumEditorStatusFilter<$PrismaModel> | $Enums.EditorStatus
  }

  export type NestedBoolWithAggregatesFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolWithAggregatesFilter<$PrismaModel> | boolean
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedBoolFilter<$PrismaModel>
    _max?: NestedBoolFilter<$PrismaModel>
  }

  export type NestedEnumEditorStatusWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.EditorStatus | EnumEditorStatusFieldRefInput<$PrismaModel>
    in?: $Enums.EditorStatus[] | ListEnumEditorStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.EditorStatus[] | ListEnumEditorStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumEditorStatusWithAggregatesFilter<$PrismaModel> | $Enums.EditorStatus
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumEditorStatusFilter<$PrismaModel>
    _max?: NestedEnumEditorStatusFilter<$PrismaModel>
  }

  export type NestedEnumInjuryStatusFilter<$PrismaModel = never> = {
    equals?: $Enums.InjuryStatus | EnumInjuryStatusFieldRefInput<$PrismaModel>
    in?: $Enums.InjuryStatus[] | ListEnumInjuryStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.InjuryStatus[] | ListEnumInjuryStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumInjuryStatusFilter<$PrismaModel> | $Enums.InjuryStatus
  }

  export type NestedEnumInjuryImpactNullableFilter<$PrismaModel = never> = {
    equals?: $Enums.InjuryImpact | EnumInjuryImpactFieldRefInput<$PrismaModel> | null
    in?: $Enums.InjuryImpact[] | ListEnumInjuryImpactFieldRefInput<$PrismaModel> | null
    notIn?: $Enums.InjuryImpact[] | ListEnumInjuryImpactFieldRefInput<$PrismaModel> | null
    not?: NestedEnumInjuryImpactNullableFilter<$PrismaModel> | $Enums.InjuryImpact | null
  }

  export type NestedEnumInjuryStatusWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.InjuryStatus | EnumInjuryStatusFieldRefInput<$PrismaModel>
    in?: $Enums.InjuryStatus[] | ListEnumInjuryStatusFieldRefInput<$PrismaModel>
    notIn?: $Enums.InjuryStatus[] | ListEnumInjuryStatusFieldRefInput<$PrismaModel>
    not?: NestedEnumInjuryStatusWithAggregatesFilter<$PrismaModel> | $Enums.InjuryStatus
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedEnumInjuryStatusFilter<$PrismaModel>
    _max?: NestedEnumInjuryStatusFilter<$PrismaModel>
  }

  export type NestedEnumInjuryImpactNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: $Enums.InjuryImpact | EnumInjuryImpactFieldRefInput<$PrismaModel> | null
    in?: $Enums.InjuryImpact[] | ListEnumInjuryImpactFieldRefInput<$PrismaModel> | null
    notIn?: $Enums.InjuryImpact[] | ListEnumInjuryImpactFieldRefInput<$PrismaModel> | null
    not?: NestedEnumInjuryImpactNullableWithAggregatesFilter<$PrismaModel> | $Enums.InjuryImpact | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedEnumInjuryImpactNullableFilter<$PrismaModel>
    _max?: NestedEnumInjuryImpactNullableFilter<$PrismaModel>
  }

  export type AccountCreateWithoutUserInput = {
    id?: string
    type: string
    provider: string
    providerAccountId: string
    refresh_token?: string | null
    access_token?: string | null
    expires_at?: number | null
    token_type?: string | null
    scope?: string | null
    id_token?: string | null
    session_state?: string | null
  }

  export type AccountUncheckedCreateWithoutUserInput = {
    id?: string
    type: string
    provider: string
    providerAccountId: string
    refresh_token?: string | null
    access_token?: string | null
    expires_at?: number | null
    token_type?: string | null
    scope?: string | null
    id_token?: string | null
    session_state?: string | null
  }

  export type AccountCreateOrConnectWithoutUserInput = {
    where: AccountWhereUniqueInput
    create: XOR<AccountCreateWithoutUserInput, AccountUncheckedCreateWithoutUserInput>
  }

  export type AccountCreateManyUserInputEnvelope = {
    data: AccountCreateManyUserInput | AccountCreateManyUserInput[]
    skipDuplicates?: boolean
  }

  export type SessionCreateWithoutUserInput = {
    id?: string
    sessionToken: string
    expires: Date | string
  }

  export type SessionUncheckedCreateWithoutUserInput = {
    id?: string
    sessionToken: string
    expires: Date | string
  }

  export type SessionCreateOrConnectWithoutUserInput = {
    where: SessionWhereUniqueInput
    create: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput>
  }

  export type SessionCreateManyUserInputEnvelope = {
    data: SessionCreateManyUserInput | SessionCreateManyUserInput[]
    skipDuplicates?: boolean
  }

  export type AccountUpsertWithWhereUniqueWithoutUserInput = {
    where: AccountWhereUniqueInput
    update: XOR<AccountUpdateWithoutUserInput, AccountUncheckedUpdateWithoutUserInput>
    create: XOR<AccountCreateWithoutUserInput, AccountUncheckedCreateWithoutUserInput>
  }

  export type AccountUpdateWithWhereUniqueWithoutUserInput = {
    where: AccountWhereUniqueInput
    data: XOR<AccountUpdateWithoutUserInput, AccountUncheckedUpdateWithoutUserInput>
  }

  export type AccountUpdateManyWithWhereWithoutUserInput = {
    where: AccountScalarWhereInput
    data: XOR<AccountUpdateManyMutationInput, AccountUncheckedUpdateManyWithoutUserInput>
  }

  export type AccountScalarWhereInput = {
    AND?: AccountScalarWhereInput | AccountScalarWhereInput[]
    OR?: AccountScalarWhereInput[]
    NOT?: AccountScalarWhereInput | AccountScalarWhereInput[]
    id?: StringFilter<"Account"> | string
    userId?: StringFilter<"Account"> | string
    type?: StringFilter<"Account"> | string
    provider?: StringFilter<"Account"> | string
    providerAccountId?: StringFilter<"Account"> | string
    refresh_token?: StringNullableFilter<"Account"> | string | null
    access_token?: StringNullableFilter<"Account"> | string | null
    expires_at?: IntNullableFilter<"Account"> | number | null
    token_type?: StringNullableFilter<"Account"> | string | null
    scope?: StringNullableFilter<"Account"> | string | null
    id_token?: StringNullableFilter<"Account"> | string | null
    session_state?: StringNullableFilter<"Account"> | string | null
  }

  export type SessionUpsertWithWhereUniqueWithoutUserInput = {
    where: SessionWhereUniqueInput
    update: XOR<SessionUpdateWithoutUserInput, SessionUncheckedUpdateWithoutUserInput>
    create: XOR<SessionCreateWithoutUserInput, SessionUncheckedCreateWithoutUserInput>
  }

  export type SessionUpdateWithWhereUniqueWithoutUserInput = {
    where: SessionWhereUniqueInput
    data: XOR<SessionUpdateWithoutUserInput, SessionUncheckedUpdateWithoutUserInput>
  }

  export type SessionUpdateManyWithWhereWithoutUserInput = {
    where: SessionScalarWhereInput
    data: XOR<SessionUpdateManyMutationInput, SessionUncheckedUpdateManyWithoutUserInput>
  }

  export type SessionScalarWhereInput = {
    AND?: SessionScalarWhereInput | SessionScalarWhereInput[]
    OR?: SessionScalarWhereInput[]
    NOT?: SessionScalarWhereInput | SessionScalarWhereInput[]
    id?: StringFilter<"Session"> | string
    sessionToken?: StringFilter<"Session"> | string
    userId?: StringFilter<"Session"> | string
    expires?: DateTimeFilter<"Session"> | Date | string
  }

  export type UserCreateWithoutAccountsInput = {
    id?: string
    email: string
    emailVerified?: Date | string | null
    name?: string | null
    password?: string | null
    image?: string | null
    role?: $Enums.UserRole
    subscriptionStatus?: $Enums.SubscriptionStatus | null
    subscriptionPlan?: string | null
    subscriptionStart?: Date | string | null
    subscriptionEnd?: Date | string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sessions?: SessionCreateNestedManyWithoutUserInput
  }

  export type UserUncheckedCreateWithoutAccountsInput = {
    id?: string
    email: string
    emailVerified?: Date | string | null
    name?: string | null
    password?: string | null
    image?: string | null
    role?: $Enums.UserRole
    subscriptionStatus?: $Enums.SubscriptionStatus | null
    subscriptionPlan?: string | null
    subscriptionStart?: Date | string | null
    subscriptionEnd?: Date | string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sessions?: SessionUncheckedCreateNestedManyWithoutUserInput
  }

  export type UserCreateOrConnectWithoutAccountsInput = {
    where: UserWhereUniqueInput
    create: XOR<UserCreateWithoutAccountsInput, UserUncheckedCreateWithoutAccountsInput>
  }

  export type UserUpsertWithoutAccountsInput = {
    update: XOR<UserUpdateWithoutAccountsInput, UserUncheckedUpdateWithoutAccountsInput>
    create: XOR<UserCreateWithoutAccountsInput, UserUncheckedCreateWithoutAccountsInput>
    where?: UserWhereInput
  }

  export type UserUpdateToOneWithWhereWithoutAccountsInput = {
    where?: UserWhereInput
    data: XOR<UserUpdateWithoutAccountsInput, UserUncheckedUpdateWithoutAccountsInput>
  }

  export type UserUpdateWithoutAccountsInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    emailVerified?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    name?: NullableStringFieldUpdateOperationsInput | string | null
    password?: NullableStringFieldUpdateOperationsInput | string | null
    image?: NullableStringFieldUpdateOperationsInput | string | null
    role?: EnumUserRoleFieldUpdateOperationsInput | $Enums.UserRole
    subscriptionStatus?: NullableEnumSubscriptionStatusFieldUpdateOperationsInput | $Enums.SubscriptionStatus | null
    subscriptionPlan?: NullableStringFieldUpdateOperationsInput | string | null
    subscriptionStart?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    subscriptionEnd?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sessions?: SessionUpdateManyWithoutUserNestedInput
  }

  export type UserUncheckedUpdateWithoutAccountsInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    emailVerified?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    name?: NullableStringFieldUpdateOperationsInput | string | null
    password?: NullableStringFieldUpdateOperationsInput | string | null
    image?: NullableStringFieldUpdateOperationsInput | string | null
    role?: EnumUserRoleFieldUpdateOperationsInput | $Enums.UserRole
    subscriptionStatus?: NullableEnumSubscriptionStatusFieldUpdateOperationsInput | $Enums.SubscriptionStatus | null
    subscriptionPlan?: NullableStringFieldUpdateOperationsInput | string | null
    subscriptionStart?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    subscriptionEnd?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sessions?: SessionUncheckedUpdateManyWithoutUserNestedInput
  }

  export type UserCreateWithoutSessionsInput = {
    id?: string
    email: string
    emailVerified?: Date | string | null
    name?: string | null
    password?: string | null
    image?: string | null
    role?: $Enums.UserRole
    subscriptionStatus?: $Enums.SubscriptionStatus | null
    subscriptionPlan?: string | null
    subscriptionStart?: Date | string | null
    subscriptionEnd?: Date | string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    accounts?: AccountCreateNestedManyWithoutUserInput
  }

  export type UserUncheckedCreateWithoutSessionsInput = {
    id?: string
    email: string
    emailVerified?: Date | string | null
    name?: string | null
    password?: string | null
    image?: string | null
    role?: $Enums.UserRole
    subscriptionStatus?: $Enums.SubscriptionStatus | null
    subscriptionPlan?: string | null
    subscriptionStart?: Date | string | null
    subscriptionEnd?: Date | string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    accounts?: AccountUncheckedCreateNestedManyWithoutUserInput
  }

  export type UserCreateOrConnectWithoutSessionsInput = {
    where: UserWhereUniqueInput
    create: XOR<UserCreateWithoutSessionsInput, UserUncheckedCreateWithoutSessionsInput>
  }

  export type UserUpsertWithoutSessionsInput = {
    update: XOR<UserUpdateWithoutSessionsInput, UserUncheckedUpdateWithoutSessionsInput>
    create: XOR<UserCreateWithoutSessionsInput, UserUncheckedCreateWithoutSessionsInput>
    where?: UserWhereInput
  }

  export type UserUpdateToOneWithWhereWithoutSessionsInput = {
    where?: UserWhereInput
    data: XOR<UserUpdateWithoutSessionsInput, UserUncheckedUpdateWithoutSessionsInput>
  }

  export type UserUpdateWithoutSessionsInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    emailVerified?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    name?: NullableStringFieldUpdateOperationsInput | string | null
    password?: NullableStringFieldUpdateOperationsInput | string | null
    image?: NullableStringFieldUpdateOperationsInput | string | null
    role?: EnumUserRoleFieldUpdateOperationsInput | $Enums.UserRole
    subscriptionStatus?: NullableEnumSubscriptionStatusFieldUpdateOperationsInput | $Enums.SubscriptionStatus | null
    subscriptionPlan?: NullableStringFieldUpdateOperationsInput | string | null
    subscriptionStart?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    subscriptionEnd?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    accounts?: AccountUpdateManyWithoutUserNestedInput
  }

  export type UserUncheckedUpdateWithoutSessionsInput = {
    id?: StringFieldUpdateOperationsInput | string
    email?: StringFieldUpdateOperationsInput | string
    emailVerified?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    name?: NullableStringFieldUpdateOperationsInput | string | null
    password?: NullableStringFieldUpdateOperationsInput | string | null
    image?: NullableStringFieldUpdateOperationsInput | string | null
    role?: EnumUserRoleFieldUpdateOperationsInput | $Enums.UserRole
    subscriptionStatus?: NullableEnumSubscriptionStatusFieldUpdateOperationsInput | $Enums.SubscriptionStatus | null
    subscriptionPlan?: NullableStringFieldUpdateOperationsInput | string | null
    subscriptionStart?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    subscriptionEnd?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    accounts?: AccountUncheckedUpdateManyWithoutUserNestedInput
  }

  export type TeamCreateWithoutSportInput = {
    id?: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    homeGames?: GameCreateNestedManyWithoutHomeTeamInput
    awayGames?: GameCreateNestedManyWithoutAwayTeamInput
    injuries?: InjuryCreateNestedManyWithoutTeamInput
    profiles?: TeamProfileWeeklyCreateNestedManyWithoutTeamInput
  }

  export type TeamUncheckedCreateWithoutSportInput = {
    id?: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    homeGames?: GameUncheckedCreateNestedManyWithoutHomeTeamInput
    awayGames?: GameUncheckedCreateNestedManyWithoutAwayTeamInput
    injuries?: InjuryUncheckedCreateNestedManyWithoutTeamInput
    profiles?: TeamProfileWeeklyUncheckedCreateNestedManyWithoutTeamInput
  }

  export type TeamCreateOrConnectWithoutSportInput = {
    where: TeamWhereUniqueInput
    create: XOR<TeamCreateWithoutSportInput, TeamUncheckedCreateWithoutSportInput>
  }

  export type TeamCreateManySportInputEnvelope = {
    data: TeamCreateManySportInput | TeamCreateManySportInput[]
    skipDuplicates?: boolean
  }

  export type GameCreateWithoutSportInput = {
    id?: string
    date: Date | string
    slug: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    homeTeam: TeamCreateNestedOneWithoutHomeGamesInput
    awayTeam: TeamCreateNestedOneWithoutAwayGamesInput
    market?: MarketSnapshotCreateNestedOneWithoutGameInput
    model?: ModelProjectionCreateNestedOneWithoutGameInput
    writeup?: WriteupCreateNestedOneWithoutGameInput
  }

  export type GameUncheckedCreateWithoutSportInput = {
    id?: string
    date: Date | string
    slug: string
    homeTeamId: string
    awayTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    market?: MarketSnapshotUncheckedCreateNestedOneWithoutGameInput
    model?: ModelProjectionUncheckedCreateNestedOneWithoutGameInput
    writeup?: WriteupUncheckedCreateNestedOneWithoutGameInput
  }

  export type GameCreateOrConnectWithoutSportInput = {
    where: GameWhereUniqueInput
    create: XOR<GameCreateWithoutSportInput, GameUncheckedCreateWithoutSportInput>
  }

  export type GameCreateManySportInputEnvelope = {
    data: GameCreateManySportInput | GameCreateManySportInput[]
    skipDuplicates?: boolean
  }

  export type TeamUpsertWithWhereUniqueWithoutSportInput = {
    where: TeamWhereUniqueInput
    update: XOR<TeamUpdateWithoutSportInput, TeamUncheckedUpdateWithoutSportInput>
    create: XOR<TeamCreateWithoutSportInput, TeamUncheckedCreateWithoutSportInput>
  }

  export type TeamUpdateWithWhereUniqueWithoutSportInput = {
    where: TeamWhereUniqueInput
    data: XOR<TeamUpdateWithoutSportInput, TeamUncheckedUpdateWithoutSportInput>
  }

  export type TeamUpdateManyWithWhereWithoutSportInput = {
    where: TeamScalarWhereInput
    data: XOR<TeamUpdateManyMutationInput, TeamUncheckedUpdateManyWithoutSportInput>
  }

  export type TeamScalarWhereInput = {
    AND?: TeamScalarWhereInput | TeamScalarWhereInput[]
    OR?: TeamScalarWhereInput[]
    NOT?: TeamScalarWhereInput | TeamScalarWhereInput[]
    id?: StringFilter<"Team"> | string
    sportId?: StringFilter<"Team"> | string
    name?: StringFilter<"Team"> | string
    slug?: StringFilter<"Team"> | string
    abbr?: StringNullableFilter<"Team"> | string | null
    createdAt?: DateTimeFilter<"Team"> | Date | string
    updatedAt?: DateTimeFilter<"Team"> | Date | string
  }

  export type GameUpsertWithWhereUniqueWithoutSportInput = {
    where: GameWhereUniqueInput
    update: XOR<GameUpdateWithoutSportInput, GameUncheckedUpdateWithoutSportInput>
    create: XOR<GameCreateWithoutSportInput, GameUncheckedCreateWithoutSportInput>
  }

  export type GameUpdateWithWhereUniqueWithoutSportInput = {
    where: GameWhereUniqueInput
    data: XOR<GameUpdateWithoutSportInput, GameUncheckedUpdateWithoutSportInput>
  }

  export type GameUpdateManyWithWhereWithoutSportInput = {
    where: GameScalarWhereInput
    data: XOR<GameUpdateManyMutationInput, GameUncheckedUpdateManyWithoutSportInput>
  }

  export type GameScalarWhereInput = {
    AND?: GameScalarWhereInput | GameScalarWhereInput[]
    OR?: GameScalarWhereInput[]
    NOT?: GameScalarWhereInput | GameScalarWhereInput[]
    id?: StringFilter<"Game"> | string
    sportId?: StringFilter<"Game"> | string
    date?: DateTimeFilter<"Game"> | Date | string
    slug?: StringFilter<"Game"> | string
    homeTeamId?: StringFilter<"Game"> | string
    awayTeamId?: StringFilter<"Game"> | string
    startTime?: DateTimeNullableFilter<"Game"> | Date | string | null
    venue?: StringNullableFilter<"Game"> | string | null
    createdAt?: DateTimeFilter<"Game"> | Date | string
    updatedAt?: DateTimeFilter<"Game"> | Date | string
  }

  export type SportCreateWithoutTeamsInput = {
    id?: string
    key: string
    name: string
    createdAt?: Date | string
    updatedAt?: Date | string
    games?: GameCreateNestedManyWithoutSportInput
  }

  export type SportUncheckedCreateWithoutTeamsInput = {
    id?: string
    key: string
    name: string
    createdAt?: Date | string
    updatedAt?: Date | string
    games?: GameUncheckedCreateNestedManyWithoutSportInput
  }

  export type SportCreateOrConnectWithoutTeamsInput = {
    where: SportWhereUniqueInput
    create: XOR<SportCreateWithoutTeamsInput, SportUncheckedCreateWithoutTeamsInput>
  }

  export type GameCreateWithoutHomeTeamInput = {
    id?: string
    date: Date | string
    slug: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutGamesInput
    awayTeam: TeamCreateNestedOneWithoutAwayGamesInput
    market?: MarketSnapshotCreateNestedOneWithoutGameInput
    model?: ModelProjectionCreateNestedOneWithoutGameInput
    writeup?: WriteupCreateNestedOneWithoutGameInput
  }

  export type GameUncheckedCreateWithoutHomeTeamInput = {
    id?: string
    sportId: string
    date: Date | string
    slug: string
    awayTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    market?: MarketSnapshotUncheckedCreateNestedOneWithoutGameInput
    model?: ModelProjectionUncheckedCreateNestedOneWithoutGameInput
    writeup?: WriteupUncheckedCreateNestedOneWithoutGameInput
  }

  export type GameCreateOrConnectWithoutHomeTeamInput = {
    where: GameWhereUniqueInput
    create: XOR<GameCreateWithoutHomeTeamInput, GameUncheckedCreateWithoutHomeTeamInput>
  }

  export type GameCreateManyHomeTeamInputEnvelope = {
    data: GameCreateManyHomeTeamInput | GameCreateManyHomeTeamInput[]
    skipDuplicates?: boolean
  }

  export type GameCreateWithoutAwayTeamInput = {
    id?: string
    date: Date | string
    slug: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutGamesInput
    homeTeam: TeamCreateNestedOneWithoutHomeGamesInput
    market?: MarketSnapshotCreateNestedOneWithoutGameInput
    model?: ModelProjectionCreateNestedOneWithoutGameInput
    writeup?: WriteupCreateNestedOneWithoutGameInput
  }

  export type GameUncheckedCreateWithoutAwayTeamInput = {
    id?: string
    sportId: string
    date: Date | string
    slug: string
    homeTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    market?: MarketSnapshotUncheckedCreateNestedOneWithoutGameInput
    model?: ModelProjectionUncheckedCreateNestedOneWithoutGameInput
    writeup?: WriteupUncheckedCreateNestedOneWithoutGameInput
  }

  export type GameCreateOrConnectWithoutAwayTeamInput = {
    where: GameWhereUniqueInput
    create: XOR<GameCreateWithoutAwayTeamInput, GameUncheckedCreateWithoutAwayTeamInput>
  }

  export type GameCreateManyAwayTeamInputEnvelope = {
    data: GameCreateManyAwayTeamInput | GameCreateManyAwayTeamInput[]
    skipDuplicates?: boolean
  }

  export type InjuryCreateWithoutTeamInput = {
    id?: string
    date: Date | string
    player: string
    status: $Enums.InjuryStatus
    note?: string | null
    impact?: $Enums.InjuryImpact | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type InjuryUncheckedCreateWithoutTeamInput = {
    id?: string
    date: Date | string
    player: string
    status: $Enums.InjuryStatus
    note?: string | null
    impact?: $Enums.InjuryImpact | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type InjuryCreateOrConnectWithoutTeamInput = {
    where: InjuryWhereUniqueInput
    create: XOR<InjuryCreateWithoutTeamInput, InjuryUncheckedCreateWithoutTeamInput>
  }

  export type InjuryCreateManyTeamInputEnvelope = {
    data: InjuryCreateManyTeamInput | InjuryCreateManyTeamInput[]
    skipDuplicates?: boolean
  }

  export type TeamProfileWeeklyCreateWithoutTeamInput = {
    id?: string
    weekStart: Date | string
    summary: string
    tempoRank?: number | null
    offPpp?: number | null
    defPpp?: number | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type TeamProfileWeeklyUncheckedCreateWithoutTeamInput = {
    id?: string
    weekStart: Date | string
    summary: string
    tempoRank?: number | null
    offPpp?: number | null
    defPpp?: number | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type TeamProfileWeeklyCreateOrConnectWithoutTeamInput = {
    where: TeamProfileWeeklyWhereUniqueInput
    create: XOR<TeamProfileWeeklyCreateWithoutTeamInput, TeamProfileWeeklyUncheckedCreateWithoutTeamInput>
  }

  export type TeamProfileWeeklyCreateManyTeamInputEnvelope = {
    data: TeamProfileWeeklyCreateManyTeamInput | TeamProfileWeeklyCreateManyTeamInput[]
    skipDuplicates?: boolean
  }

  export type SportUpsertWithoutTeamsInput = {
    update: XOR<SportUpdateWithoutTeamsInput, SportUncheckedUpdateWithoutTeamsInput>
    create: XOR<SportCreateWithoutTeamsInput, SportUncheckedCreateWithoutTeamsInput>
    where?: SportWhereInput
  }

  export type SportUpdateToOneWithWhereWithoutTeamsInput = {
    where?: SportWhereInput
    data: XOR<SportUpdateWithoutTeamsInput, SportUncheckedUpdateWithoutTeamsInput>
  }

  export type SportUpdateWithoutTeamsInput = {
    id?: StringFieldUpdateOperationsInput | string
    key?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    games?: GameUpdateManyWithoutSportNestedInput
  }

  export type SportUncheckedUpdateWithoutTeamsInput = {
    id?: StringFieldUpdateOperationsInput | string
    key?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    games?: GameUncheckedUpdateManyWithoutSportNestedInput
  }

  export type GameUpsertWithWhereUniqueWithoutHomeTeamInput = {
    where: GameWhereUniqueInput
    update: XOR<GameUpdateWithoutHomeTeamInput, GameUncheckedUpdateWithoutHomeTeamInput>
    create: XOR<GameCreateWithoutHomeTeamInput, GameUncheckedCreateWithoutHomeTeamInput>
  }

  export type GameUpdateWithWhereUniqueWithoutHomeTeamInput = {
    where: GameWhereUniqueInput
    data: XOR<GameUpdateWithoutHomeTeamInput, GameUncheckedUpdateWithoutHomeTeamInput>
  }

  export type GameUpdateManyWithWhereWithoutHomeTeamInput = {
    where: GameScalarWhereInput
    data: XOR<GameUpdateManyMutationInput, GameUncheckedUpdateManyWithoutHomeTeamInput>
  }

  export type GameUpsertWithWhereUniqueWithoutAwayTeamInput = {
    where: GameWhereUniqueInput
    update: XOR<GameUpdateWithoutAwayTeamInput, GameUncheckedUpdateWithoutAwayTeamInput>
    create: XOR<GameCreateWithoutAwayTeamInput, GameUncheckedCreateWithoutAwayTeamInput>
  }

  export type GameUpdateWithWhereUniqueWithoutAwayTeamInput = {
    where: GameWhereUniqueInput
    data: XOR<GameUpdateWithoutAwayTeamInput, GameUncheckedUpdateWithoutAwayTeamInput>
  }

  export type GameUpdateManyWithWhereWithoutAwayTeamInput = {
    where: GameScalarWhereInput
    data: XOR<GameUpdateManyMutationInput, GameUncheckedUpdateManyWithoutAwayTeamInput>
  }

  export type InjuryUpsertWithWhereUniqueWithoutTeamInput = {
    where: InjuryWhereUniqueInput
    update: XOR<InjuryUpdateWithoutTeamInput, InjuryUncheckedUpdateWithoutTeamInput>
    create: XOR<InjuryCreateWithoutTeamInput, InjuryUncheckedCreateWithoutTeamInput>
  }

  export type InjuryUpdateWithWhereUniqueWithoutTeamInput = {
    where: InjuryWhereUniqueInput
    data: XOR<InjuryUpdateWithoutTeamInput, InjuryUncheckedUpdateWithoutTeamInput>
  }

  export type InjuryUpdateManyWithWhereWithoutTeamInput = {
    where: InjuryScalarWhereInput
    data: XOR<InjuryUpdateManyMutationInput, InjuryUncheckedUpdateManyWithoutTeamInput>
  }

  export type InjuryScalarWhereInput = {
    AND?: InjuryScalarWhereInput | InjuryScalarWhereInput[]
    OR?: InjuryScalarWhereInput[]
    NOT?: InjuryScalarWhereInput | InjuryScalarWhereInput[]
    id?: StringFilter<"Injury"> | string
    teamId?: StringFilter<"Injury"> | string
    date?: DateTimeFilter<"Injury"> | Date | string
    player?: StringFilter<"Injury"> | string
    status?: EnumInjuryStatusFilter<"Injury"> | $Enums.InjuryStatus
    note?: StringNullableFilter<"Injury"> | string | null
    impact?: EnumInjuryImpactNullableFilter<"Injury"> | $Enums.InjuryImpact | null
    createdAt?: DateTimeFilter<"Injury"> | Date | string
    updatedAt?: DateTimeFilter<"Injury"> | Date | string
  }

  export type TeamProfileWeeklyUpsertWithWhereUniqueWithoutTeamInput = {
    where: TeamProfileWeeklyWhereUniqueInput
    update: XOR<TeamProfileWeeklyUpdateWithoutTeamInput, TeamProfileWeeklyUncheckedUpdateWithoutTeamInput>
    create: XOR<TeamProfileWeeklyCreateWithoutTeamInput, TeamProfileWeeklyUncheckedCreateWithoutTeamInput>
  }

  export type TeamProfileWeeklyUpdateWithWhereUniqueWithoutTeamInput = {
    where: TeamProfileWeeklyWhereUniqueInput
    data: XOR<TeamProfileWeeklyUpdateWithoutTeamInput, TeamProfileWeeklyUncheckedUpdateWithoutTeamInput>
  }

  export type TeamProfileWeeklyUpdateManyWithWhereWithoutTeamInput = {
    where: TeamProfileWeeklyScalarWhereInput
    data: XOR<TeamProfileWeeklyUpdateManyMutationInput, TeamProfileWeeklyUncheckedUpdateManyWithoutTeamInput>
  }

  export type TeamProfileWeeklyScalarWhereInput = {
    AND?: TeamProfileWeeklyScalarWhereInput | TeamProfileWeeklyScalarWhereInput[]
    OR?: TeamProfileWeeklyScalarWhereInput[]
    NOT?: TeamProfileWeeklyScalarWhereInput | TeamProfileWeeklyScalarWhereInput[]
    id?: StringFilter<"TeamProfileWeekly"> | string
    teamId?: StringFilter<"TeamProfileWeekly"> | string
    weekStart?: DateTimeFilter<"TeamProfileWeekly"> | Date | string
    summary?: StringFilter<"TeamProfileWeekly"> | string
    tempoRank?: IntNullableFilter<"TeamProfileWeekly"> | number | null
    offPpp?: FloatNullableFilter<"TeamProfileWeekly"> | number | null
    defPpp?: FloatNullableFilter<"TeamProfileWeekly"> | number | null
    createdAt?: DateTimeFilter<"TeamProfileWeekly"> | Date | string
    updatedAt?: DateTimeFilter<"TeamProfileWeekly"> | Date | string
  }

  export type SportCreateWithoutGamesInput = {
    id?: string
    key: string
    name: string
    createdAt?: Date | string
    updatedAt?: Date | string
    teams?: TeamCreateNestedManyWithoutSportInput
  }

  export type SportUncheckedCreateWithoutGamesInput = {
    id?: string
    key: string
    name: string
    createdAt?: Date | string
    updatedAt?: Date | string
    teams?: TeamUncheckedCreateNestedManyWithoutSportInput
  }

  export type SportCreateOrConnectWithoutGamesInput = {
    where: SportWhereUniqueInput
    create: XOR<SportCreateWithoutGamesInput, SportUncheckedCreateWithoutGamesInput>
  }

  export type TeamCreateWithoutHomeGamesInput = {
    id?: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutTeamsInput
    awayGames?: GameCreateNestedManyWithoutAwayTeamInput
    injuries?: InjuryCreateNestedManyWithoutTeamInput
    profiles?: TeamProfileWeeklyCreateNestedManyWithoutTeamInput
  }

  export type TeamUncheckedCreateWithoutHomeGamesInput = {
    id?: string
    sportId: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    awayGames?: GameUncheckedCreateNestedManyWithoutAwayTeamInput
    injuries?: InjuryUncheckedCreateNestedManyWithoutTeamInput
    profiles?: TeamProfileWeeklyUncheckedCreateNestedManyWithoutTeamInput
  }

  export type TeamCreateOrConnectWithoutHomeGamesInput = {
    where: TeamWhereUniqueInput
    create: XOR<TeamCreateWithoutHomeGamesInput, TeamUncheckedCreateWithoutHomeGamesInput>
  }

  export type TeamCreateWithoutAwayGamesInput = {
    id?: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutTeamsInput
    homeGames?: GameCreateNestedManyWithoutHomeTeamInput
    injuries?: InjuryCreateNestedManyWithoutTeamInput
    profiles?: TeamProfileWeeklyCreateNestedManyWithoutTeamInput
  }

  export type TeamUncheckedCreateWithoutAwayGamesInput = {
    id?: string
    sportId: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    homeGames?: GameUncheckedCreateNestedManyWithoutHomeTeamInput
    injuries?: InjuryUncheckedCreateNestedManyWithoutTeamInput
    profiles?: TeamProfileWeeklyUncheckedCreateNestedManyWithoutTeamInput
  }

  export type TeamCreateOrConnectWithoutAwayGamesInput = {
    where: TeamWhereUniqueInput
    create: XOR<TeamCreateWithoutAwayGamesInput, TeamUncheckedCreateWithoutAwayGamesInput>
  }

  export type MarketSnapshotCreateWithoutGameInput = {
    id?: string
    capturedAt?: Date | string
    openSpreadHome?: number | null
    currentSpreadHome?: number | null
    openTotal?: number | null
    currentTotal?: number | null
    bestSpreadHome?: number | null
    bestSpreadBook?: string | null
    bestTotal?: number | null
    bestTotalBook?: string | null
    spreadDispersion?: number | null
    totalDispersion?: number | null
    bookLines?: BookLineCreateNestedManyWithoutMarketInput
  }

  export type MarketSnapshotUncheckedCreateWithoutGameInput = {
    id?: string
    capturedAt?: Date | string
    openSpreadHome?: number | null
    currentSpreadHome?: number | null
    openTotal?: number | null
    currentTotal?: number | null
    bestSpreadHome?: number | null
    bestSpreadBook?: string | null
    bestTotal?: number | null
    bestTotalBook?: string | null
    spreadDispersion?: number | null
    totalDispersion?: number | null
    bookLines?: BookLineUncheckedCreateNestedManyWithoutMarketInput
  }

  export type MarketSnapshotCreateOrConnectWithoutGameInput = {
    where: MarketSnapshotWhereUniqueInput
    create: XOR<MarketSnapshotCreateWithoutGameInput, MarketSnapshotUncheckedCreateWithoutGameInput>
  }

  export type ModelProjectionCreateWithoutGameInput = {
    id?: string
    version: string
    computedAt?: Date | string
    projSpreadHome: number
    projTotal: number
  }

  export type ModelProjectionUncheckedCreateWithoutGameInput = {
    id?: string
    version: string
    computedAt?: Date | string
    projSpreadHome: number
    projTotal: number
  }

  export type ModelProjectionCreateOrConnectWithoutGameInput = {
    where: ModelProjectionWhereUniqueInput
    create: XOR<ModelProjectionCreateWithoutGameInput, ModelProjectionUncheckedCreateWithoutGameInput>
  }

  export type WriteupCreateWithoutGameInput = {
    id?: string
    createdAt?: Date | string
    updatedAt?: Date | string
    formatKey: string
    body: string
    disclosedAi?: boolean
    editorStatus?: $Enums.EditorStatus
  }

  export type WriteupUncheckedCreateWithoutGameInput = {
    id?: string
    createdAt?: Date | string
    updatedAt?: Date | string
    formatKey: string
    body: string
    disclosedAi?: boolean
    editorStatus?: $Enums.EditorStatus
  }

  export type WriteupCreateOrConnectWithoutGameInput = {
    where: WriteupWhereUniqueInput
    create: XOR<WriteupCreateWithoutGameInput, WriteupUncheckedCreateWithoutGameInput>
  }

  export type SportUpsertWithoutGamesInput = {
    update: XOR<SportUpdateWithoutGamesInput, SportUncheckedUpdateWithoutGamesInput>
    create: XOR<SportCreateWithoutGamesInput, SportUncheckedCreateWithoutGamesInput>
    where?: SportWhereInput
  }

  export type SportUpdateToOneWithWhereWithoutGamesInput = {
    where?: SportWhereInput
    data: XOR<SportUpdateWithoutGamesInput, SportUncheckedUpdateWithoutGamesInput>
  }

  export type SportUpdateWithoutGamesInput = {
    id?: StringFieldUpdateOperationsInput | string
    key?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    teams?: TeamUpdateManyWithoutSportNestedInput
  }

  export type SportUncheckedUpdateWithoutGamesInput = {
    id?: StringFieldUpdateOperationsInput | string
    key?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    teams?: TeamUncheckedUpdateManyWithoutSportNestedInput
  }

  export type TeamUpsertWithoutHomeGamesInput = {
    update: XOR<TeamUpdateWithoutHomeGamesInput, TeamUncheckedUpdateWithoutHomeGamesInput>
    create: XOR<TeamCreateWithoutHomeGamesInput, TeamUncheckedCreateWithoutHomeGamesInput>
    where?: TeamWhereInput
  }

  export type TeamUpdateToOneWithWhereWithoutHomeGamesInput = {
    where?: TeamWhereInput
    data: XOR<TeamUpdateWithoutHomeGamesInput, TeamUncheckedUpdateWithoutHomeGamesInput>
  }

  export type TeamUpdateWithoutHomeGamesInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutTeamsNestedInput
    awayGames?: GameUpdateManyWithoutAwayTeamNestedInput
    injuries?: InjuryUpdateManyWithoutTeamNestedInput
    profiles?: TeamProfileWeeklyUpdateManyWithoutTeamNestedInput
  }

  export type TeamUncheckedUpdateWithoutHomeGamesInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    awayGames?: GameUncheckedUpdateManyWithoutAwayTeamNestedInput
    injuries?: InjuryUncheckedUpdateManyWithoutTeamNestedInput
    profiles?: TeamProfileWeeklyUncheckedUpdateManyWithoutTeamNestedInput
  }

  export type TeamUpsertWithoutAwayGamesInput = {
    update: XOR<TeamUpdateWithoutAwayGamesInput, TeamUncheckedUpdateWithoutAwayGamesInput>
    create: XOR<TeamCreateWithoutAwayGamesInput, TeamUncheckedCreateWithoutAwayGamesInput>
    where?: TeamWhereInput
  }

  export type TeamUpdateToOneWithWhereWithoutAwayGamesInput = {
    where?: TeamWhereInput
    data: XOR<TeamUpdateWithoutAwayGamesInput, TeamUncheckedUpdateWithoutAwayGamesInput>
  }

  export type TeamUpdateWithoutAwayGamesInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutTeamsNestedInput
    homeGames?: GameUpdateManyWithoutHomeTeamNestedInput
    injuries?: InjuryUpdateManyWithoutTeamNestedInput
    profiles?: TeamProfileWeeklyUpdateManyWithoutTeamNestedInput
  }

  export type TeamUncheckedUpdateWithoutAwayGamesInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    homeGames?: GameUncheckedUpdateManyWithoutHomeTeamNestedInput
    injuries?: InjuryUncheckedUpdateManyWithoutTeamNestedInput
    profiles?: TeamProfileWeeklyUncheckedUpdateManyWithoutTeamNestedInput
  }

  export type MarketSnapshotUpsertWithoutGameInput = {
    update: XOR<MarketSnapshotUpdateWithoutGameInput, MarketSnapshotUncheckedUpdateWithoutGameInput>
    create: XOR<MarketSnapshotCreateWithoutGameInput, MarketSnapshotUncheckedCreateWithoutGameInput>
    where?: MarketSnapshotWhereInput
  }

  export type MarketSnapshotUpdateToOneWithWhereWithoutGameInput = {
    where?: MarketSnapshotWhereInput
    data: XOR<MarketSnapshotUpdateWithoutGameInput, MarketSnapshotUncheckedUpdateWithoutGameInput>
  }

  export type MarketSnapshotUpdateWithoutGameInput = {
    id?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    openSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    currentSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    openTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    currentTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadBook?: NullableStringFieldUpdateOperationsInput | string | null
    bestTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestTotalBook?: NullableStringFieldUpdateOperationsInput | string | null
    spreadDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    totalDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    bookLines?: BookLineUpdateManyWithoutMarketNestedInput
  }

  export type MarketSnapshotUncheckedUpdateWithoutGameInput = {
    id?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    openSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    currentSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    openTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    currentTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadBook?: NullableStringFieldUpdateOperationsInput | string | null
    bestTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestTotalBook?: NullableStringFieldUpdateOperationsInput | string | null
    spreadDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    totalDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    bookLines?: BookLineUncheckedUpdateManyWithoutMarketNestedInput
  }

  export type ModelProjectionUpsertWithoutGameInput = {
    update: XOR<ModelProjectionUpdateWithoutGameInput, ModelProjectionUncheckedUpdateWithoutGameInput>
    create: XOR<ModelProjectionCreateWithoutGameInput, ModelProjectionUncheckedCreateWithoutGameInput>
    where?: ModelProjectionWhereInput
  }

  export type ModelProjectionUpdateToOneWithWhereWithoutGameInput = {
    where?: ModelProjectionWhereInput
    data: XOR<ModelProjectionUpdateWithoutGameInput, ModelProjectionUncheckedUpdateWithoutGameInput>
  }

  export type ModelProjectionUpdateWithoutGameInput = {
    id?: StringFieldUpdateOperationsInput | string
    version?: StringFieldUpdateOperationsInput | string
    computedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    projSpreadHome?: FloatFieldUpdateOperationsInput | number
    projTotal?: FloatFieldUpdateOperationsInput | number
  }

  export type ModelProjectionUncheckedUpdateWithoutGameInput = {
    id?: StringFieldUpdateOperationsInput | string
    version?: StringFieldUpdateOperationsInput | string
    computedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    projSpreadHome?: FloatFieldUpdateOperationsInput | number
    projTotal?: FloatFieldUpdateOperationsInput | number
  }

  export type WriteupUpsertWithoutGameInput = {
    update: XOR<WriteupUpdateWithoutGameInput, WriteupUncheckedUpdateWithoutGameInput>
    create: XOR<WriteupCreateWithoutGameInput, WriteupUncheckedCreateWithoutGameInput>
    where?: WriteupWhereInput
  }

  export type WriteupUpdateToOneWithWhereWithoutGameInput = {
    where?: WriteupWhereInput
    data: XOR<WriteupUpdateWithoutGameInput, WriteupUncheckedUpdateWithoutGameInput>
  }

  export type WriteupUpdateWithoutGameInput = {
    id?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    formatKey?: StringFieldUpdateOperationsInput | string
    body?: StringFieldUpdateOperationsInput | string
    disclosedAi?: BoolFieldUpdateOperationsInput | boolean
    editorStatus?: EnumEditorStatusFieldUpdateOperationsInput | $Enums.EditorStatus
  }

  export type WriteupUncheckedUpdateWithoutGameInput = {
    id?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    formatKey?: StringFieldUpdateOperationsInput | string
    body?: StringFieldUpdateOperationsInput | string
    disclosedAi?: BoolFieldUpdateOperationsInput | boolean
    editorStatus?: EnumEditorStatusFieldUpdateOperationsInput | $Enums.EditorStatus
  }

  export type BookLineCreateWithoutMarketInput = {
    id?: string
    book: string
    capturedAt?: Date | string
    spreadHome?: number | null
    spreadAway?: number | null
    total?: number | null
  }

  export type BookLineUncheckedCreateWithoutMarketInput = {
    id?: string
    book: string
    capturedAt?: Date | string
    spreadHome?: number | null
    spreadAway?: number | null
    total?: number | null
  }

  export type BookLineCreateOrConnectWithoutMarketInput = {
    where: BookLineWhereUniqueInput
    create: XOR<BookLineCreateWithoutMarketInput, BookLineUncheckedCreateWithoutMarketInput>
  }

  export type BookLineCreateManyMarketInputEnvelope = {
    data: BookLineCreateManyMarketInput | BookLineCreateManyMarketInput[]
    skipDuplicates?: boolean
  }

  export type GameCreateWithoutMarketInput = {
    id?: string
    date: Date | string
    slug: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutGamesInput
    homeTeam: TeamCreateNestedOneWithoutHomeGamesInput
    awayTeam: TeamCreateNestedOneWithoutAwayGamesInput
    model?: ModelProjectionCreateNestedOneWithoutGameInput
    writeup?: WriteupCreateNestedOneWithoutGameInput
  }

  export type GameUncheckedCreateWithoutMarketInput = {
    id?: string
    sportId: string
    date: Date | string
    slug: string
    homeTeamId: string
    awayTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    model?: ModelProjectionUncheckedCreateNestedOneWithoutGameInput
    writeup?: WriteupUncheckedCreateNestedOneWithoutGameInput
  }

  export type GameCreateOrConnectWithoutMarketInput = {
    where: GameWhereUniqueInput
    create: XOR<GameCreateWithoutMarketInput, GameUncheckedCreateWithoutMarketInput>
  }

  export type BookLineUpsertWithWhereUniqueWithoutMarketInput = {
    where: BookLineWhereUniqueInput
    update: XOR<BookLineUpdateWithoutMarketInput, BookLineUncheckedUpdateWithoutMarketInput>
    create: XOR<BookLineCreateWithoutMarketInput, BookLineUncheckedCreateWithoutMarketInput>
  }

  export type BookLineUpdateWithWhereUniqueWithoutMarketInput = {
    where: BookLineWhereUniqueInput
    data: XOR<BookLineUpdateWithoutMarketInput, BookLineUncheckedUpdateWithoutMarketInput>
  }

  export type BookLineUpdateManyWithWhereWithoutMarketInput = {
    where: BookLineScalarWhereInput
    data: XOR<BookLineUpdateManyMutationInput, BookLineUncheckedUpdateManyWithoutMarketInput>
  }

  export type BookLineScalarWhereInput = {
    AND?: BookLineScalarWhereInput | BookLineScalarWhereInput[]
    OR?: BookLineScalarWhereInput[]
    NOT?: BookLineScalarWhereInput | BookLineScalarWhereInput[]
    id?: StringFilter<"BookLine"> | string
    marketId?: StringFilter<"BookLine"> | string
    book?: StringFilter<"BookLine"> | string
    capturedAt?: DateTimeFilter<"BookLine"> | Date | string
    spreadHome?: FloatNullableFilter<"BookLine"> | number | null
    spreadAway?: FloatNullableFilter<"BookLine"> | number | null
    total?: FloatNullableFilter<"BookLine"> | number | null
  }

  export type GameUpsertWithoutMarketInput = {
    update: XOR<GameUpdateWithoutMarketInput, GameUncheckedUpdateWithoutMarketInput>
    create: XOR<GameCreateWithoutMarketInput, GameUncheckedCreateWithoutMarketInput>
    where?: GameWhereInput
  }

  export type GameUpdateToOneWithWhereWithoutMarketInput = {
    where?: GameWhereInput
    data: XOR<GameUpdateWithoutMarketInput, GameUncheckedUpdateWithoutMarketInput>
  }

  export type GameUpdateWithoutMarketInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutGamesNestedInput
    homeTeam?: TeamUpdateOneRequiredWithoutHomeGamesNestedInput
    awayTeam?: TeamUpdateOneRequiredWithoutAwayGamesNestedInput
    model?: ModelProjectionUpdateOneWithoutGameNestedInput
    writeup?: WriteupUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateWithoutMarketInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    homeTeamId?: StringFieldUpdateOperationsInput | string
    awayTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    model?: ModelProjectionUncheckedUpdateOneWithoutGameNestedInput
    writeup?: WriteupUncheckedUpdateOneWithoutGameNestedInput
  }

  export type MarketSnapshotCreateWithoutBookLinesInput = {
    id?: string
    capturedAt?: Date | string
    openSpreadHome?: number | null
    currentSpreadHome?: number | null
    openTotal?: number | null
    currentTotal?: number | null
    bestSpreadHome?: number | null
    bestSpreadBook?: string | null
    bestTotal?: number | null
    bestTotalBook?: string | null
    spreadDispersion?: number | null
    totalDispersion?: number | null
    game: GameCreateNestedOneWithoutMarketInput
  }

  export type MarketSnapshotUncheckedCreateWithoutBookLinesInput = {
    id?: string
    gameId: string
    capturedAt?: Date | string
    openSpreadHome?: number | null
    currentSpreadHome?: number | null
    openTotal?: number | null
    currentTotal?: number | null
    bestSpreadHome?: number | null
    bestSpreadBook?: string | null
    bestTotal?: number | null
    bestTotalBook?: string | null
    spreadDispersion?: number | null
    totalDispersion?: number | null
  }

  export type MarketSnapshotCreateOrConnectWithoutBookLinesInput = {
    where: MarketSnapshotWhereUniqueInput
    create: XOR<MarketSnapshotCreateWithoutBookLinesInput, MarketSnapshotUncheckedCreateWithoutBookLinesInput>
  }

  export type MarketSnapshotUpsertWithoutBookLinesInput = {
    update: XOR<MarketSnapshotUpdateWithoutBookLinesInput, MarketSnapshotUncheckedUpdateWithoutBookLinesInput>
    create: XOR<MarketSnapshotCreateWithoutBookLinesInput, MarketSnapshotUncheckedCreateWithoutBookLinesInput>
    where?: MarketSnapshotWhereInput
  }

  export type MarketSnapshotUpdateToOneWithWhereWithoutBookLinesInput = {
    where?: MarketSnapshotWhereInput
    data: XOR<MarketSnapshotUpdateWithoutBookLinesInput, MarketSnapshotUncheckedUpdateWithoutBookLinesInput>
  }

  export type MarketSnapshotUpdateWithoutBookLinesInput = {
    id?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    openSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    currentSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    openTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    currentTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadBook?: NullableStringFieldUpdateOperationsInput | string | null
    bestTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestTotalBook?: NullableStringFieldUpdateOperationsInput | string | null
    spreadDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    totalDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    game?: GameUpdateOneRequiredWithoutMarketNestedInput
  }

  export type MarketSnapshotUncheckedUpdateWithoutBookLinesInput = {
    id?: StringFieldUpdateOperationsInput | string
    gameId?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    openSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    currentSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    openTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    currentTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    bestSpreadBook?: NullableStringFieldUpdateOperationsInput | string | null
    bestTotal?: NullableFloatFieldUpdateOperationsInput | number | null
    bestTotalBook?: NullableStringFieldUpdateOperationsInput | string | null
    spreadDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
    totalDispersion?: NullableFloatFieldUpdateOperationsInput | number | null
  }

  export type GameCreateWithoutModelInput = {
    id?: string
    date: Date | string
    slug: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutGamesInput
    homeTeam: TeamCreateNestedOneWithoutHomeGamesInput
    awayTeam: TeamCreateNestedOneWithoutAwayGamesInput
    market?: MarketSnapshotCreateNestedOneWithoutGameInput
    writeup?: WriteupCreateNestedOneWithoutGameInput
  }

  export type GameUncheckedCreateWithoutModelInput = {
    id?: string
    sportId: string
    date: Date | string
    slug: string
    homeTeamId: string
    awayTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    market?: MarketSnapshotUncheckedCreateNestedOneWithoutGameInput
    writeup?: WriteupUncheckedCreateNestedOneWithoutGameInput
  }

  export type GameCreateOrConnectWithoutModelInput = {
    where: GameWhereUniqueInput
    create: XOR<GameCreateWithoutModelInput, GameUncheckedCreateWithoutModelInput>
  }

  export type GameUpsertWithoutModelInput = {
    update: XOR<GameUpdateWithoutModelInput, GameUncheckedUpdateWithoutModelInput>
    create: XOR<GameCreateWithoutModelInput, GameUncheckedCreateWithoutModelInput>
    where?: GameWhereInput
  }

  export type GameUpdateToOneWithWhereWithoutModelInput = {
    where?: GameWhereInput
    data: XOR<GameUpdateWithoutModelInput, GameUncheckedUpdateWithoutModelInput>
  }

  export type GameUpdateWithoutModelInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutGamesNestedInput
    homeTeam?: TeamUpdateOneRequiredWithoutHomeGamesNestedInput
    awayTeam?: TeamUpdateOneRequiredWithoutAwayGamesNestedInput
    market?: MarketSnapshotUpdateOneWithoutGameNestedInput
    writeup?: WriteupUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateWithoutModelInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    homeTeamId?: StringFieldUpdateOperationsInput | string
    awayTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    market?: MarketSnapshotUncheckedUpdateOneWithoutGameNestedInput
    writeup?: WriteupUncheckedUpdateOneWithoutGameNestedInput
  }

  export type GameCreateWithoutWriteupInput = {
    id?: string
    date: Date | string
    slug: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutGamesInput
    homeTeam: TeamCreateNestedOneWithoutHomeGamesInput
    awayTeam: TeamCreateNestedOneWithoutAwayGamesInput
    market?: MarketSnapshotCreateNestedOneWithoutGameInput
    model?: ModelProjectionCreateNestedOneWithoutGameInput
  }

  export type GameUncheckedCreateWithoutWriteupInput = {
    id?: string
    sportId: string
    date: Date | string
    slug: string
    homeTeamId: string
    awayTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    market?: MarketSnapshotUncheckedCreateNestedOneWithoutGameInput
    model?: ModelProjectionUncheckedCreateNestedOneWithoutGameInput
  }

  export type GameCreateOrConnectWithoutWriteupInput = {
    where: GameWhereUniqueInput
    create: XOR<GameCreateWithoutWriteupInput, GameUncheckedCreateWithoutWriteupInput>
  }

  export type GameUpsertWithoutWriteupInput = {
    update: XOR<GameUpdateWithoutWriteupInput, GameUncheckedUpdateWithoutWriteupInput>
    create: XOR<GameCreateWithoutWriteupInput, GameUncheckedCreateWithoutWriteupInput>
    where?: GameWhereInput
  }

  export type GameUpdateToOneWithWhereWithoutWriteupInput = {
    where?: GameWhereInput
    data: XOR<GameUpdateWithoutWriteupInput, GameUncheckedUpdateWithoutWriteupInput>
  }

  export type GameUpdateWithoutWriteupInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutGamesNestedInput
    homeTeam?: TeamUpdateOneRequiredWithoutHomeGamesNestedInput
    awayTeam?: TeamUpdateOneRequiredWithoutAwayGamesNestedInput
    market?: MarketSnapshotUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateWithoutWriteupInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    homeTeamId?: StringFieldUpdateOperationsInput | string
    awayTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    market?: MarketSnapshotUncheckedUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUncheckedUpdateOneWithoutGameNestedInput
  }

  export type TeamCreateWithoutInjuriesInput = {
    id?: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutTeamsInput
    homeGames?: GameCreateNestedManyWithoutHomeTeamInput
    awayGames?: GameCreateNestedManyWithoutAwayTeamInput
    profiles?: TeamProfileWeeklyCreateNestedManyWithoutTeamInput
  }

  export type TeamUncheckedCreateWithoutInjuriesInput = {
    id?: string
    sportId: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    homeGames?: GameUncheckedCreateNestedManyWithoutHomeTeamInput
    awayGames?: GameUncheckedCreateNestedManyWithoutAwayTeamInput
    profiles?: TeamProfileWeeklyUncheckedCreateNestedManyWithoutTeamInput
  }

  export type TeamCreateOrConnectWithoutInjuriesInput = {
    where: TeamWhereUniqueInput
    create: XOR<TeamCreateWithoutInjuriesInput, TeamUncheckedCreateWithoutInjuriesInput>
  }

  export type TeamUpsertWithoutInjuriesInput = {
    update: XOR<TeamUpdateWithoutInjuriesInput, TeamUncheckedUpdateWithoutInjuriesInput>
    create: XOR<TeamCreateWithoutInjuriesInput, TeamUncheckedCreateWithoutInjuriesInput>
    where?: TeamWhereInput
  }

  export type TeamUpdateToOneWithWhereWithoutInjuriesInput = {
    where?: TeamWhereInput
    data: XOR<TeamUpdateWithoutInjuriesInput, TeamUncheckedUpdateWithoutInjuriesInput>
  }

  export type TeamUpdateWithoutInjuriesInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutTeamsNestedInput
    homeGames?: GameUpdateManyWithoutHomeTeamNestedInput
    awayGames?: GameUpdateManyWithoutAwayTeamNestedInput
    profiles?: TeamProfileWeeklyUpdateManyWithoutTeamNestedInput
  }

  export type TeamUncheckedUpdateWithoutInjuriesInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    homeGames?: GameUncheckedUpdateManyWithoutHomeTeamNestedInput
    awayGames?: GameUncheckedUpdateManyWithoutAwayTeamNestedInput
    profiles?: TeamProfileWeeklyUncheckedUpdateManyWithoutTeamNestedInput
  }

  export type TeamCreateWithoutProfilesInput = {
    id?: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    sport: SportCreateNestedOneWithoutTeamsInput
    homeGames?: GameCreateNestedManyWithoutHomeTeamInput
    awayGames?: GameCreateNestedManyWithoutAwayTeamInput
    injuries?: InjuryCreateNestedManyWithoutTeamInput
  }

  export type TeamUncheckedCreateWithoutProfilesInput = {
    id?: string
    sportId: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
    homeGames?: GameUncheckedCreateNestedManyWithoutHomeTeamInput
    awayGames?: GameUncheckedCreateNestedManyWithoutAwayTeamInput
    injuries?: InjuryUncheckedCreateNestedManyWithoutTeamInput
  }

  export type TeamCreateOrConnectWithoutProfilesInput = {
    where: TeamWhereUniqueInput
    create: XOR<TeamCreateWithoutProfilesInput, TeamUncheckedCreateWithoutProfilesInput>
  }

  export type TeamUpsertWithoutProfilesInput = {
    update: XOR<TeamUpdateWithoutProfilesInput, TeamUncheckedUpdateWithoutProfilesInput>
    create: XOR<TeamCreateWithoutProfilesInput, TeamUncheckedCreateWithoutProfilesInput>
    where?: TeamWhereInput
  }

  export type TeamUpdateToOneWithWhereWithoutProfilesInput = {
    where?: TeamWhereInput
    data: XOR<TeamUpdateWithoutProfilesInput, TeamUncheckedUpdateWithoutProfilesInput>
  }

  export type TeamUpdateWithoutProfilesInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutTeamsNestedInput
    homeGames?: GameUpdateManyWithoutHomeTeamNestedInput
    awayGames?: GameUpdateManyWithoutAwayTeamNestedInput
    injuries?: InjuryUpdateManyWithoutTeamNestedInput
  }

  export type TeamUncheckedUpdateWithoutProfilesInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    homeGames?: GameUncheckedUpdateManyWithoutHomeTeamNestedInput
    awayGames?: GameUncheckedUpdateManyWithoutAwayTeamNestedInput
    injuries?: InjuryUncheckedUpdateManyWithoutTeamNestedInput
  }

  export type AccountCreateManyUserInput = {
    id?: string
    type: string
    provider: string
    providerAccountId: string
    refresh_token?: string | null
    access_token?: string | null
    expires_at?: number | null
    token_type?: string | null
    scope?: string | null
    id_token?: string | null
    session_state?: string | null
  }

  export type SessionCreateManyUserInput = {
    id?: string
    sessionToken: string
    expires: Date | string
  }

  export type AccountUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    provider?: StringFieldUpdateOperationsInput | string
    providerAccountId?: StringFieldUpdateOperationsInput | string
    refresh_token?: NullableStringFieldUpdateOperationsInput | string | null
    access_token?: NullableStringFieldUpdateOperationsInput | string | null
    expires_at?: NullableIntFieldUpdateOperationsInput | number | null
    token_type?: NullableStringFieldUpdateOperationsInput | string | null
    scope?: NullableStringFieldUpdateOperationsInput | string | null
    id_token?: NullableStringFieldUpdateOperationsInput | string | null
    session_state?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type AccountUncheckedUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    provider?: StringFieldUpdateOperationsInput | string
    providerAccountId?: StringFieldUpdateOperationsInput | string
    refresh_token?: NullableStringFieldUpdateOperationsInput | string | null
    access_token?: NullableStringFieldUpdateOperationsInput | string | null
    expires_at?: NullableIntFieldUpdateOperationsInput | number | null
    token_type?: NullableStringFieldUpdateOperationsInput | string | null
    scope?: NullableStringFieldUpdateOperationsInput | string | null
    id_token?: NullableStringFieldUpdateOperationsInput | string | null
    session_state?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type AccountUncheckedUpdateManyWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    provider?: StringFieldUpdateOperationsInput | string
    providerAccountId?: StringFieldUpdateOperationsInput | string
    refresh_token?: NullableStringFieldUpdateOperationsInput | string | null
    access_token?: NullableStringFieldUpdateOperationsInput | string | null
    expires_at?: NullableIntFieldUpdateOperationsInput | number | null
    token_type?: NullableStringFieldUpdateOperationsInput | string | null
    scope?: NullableStringFieldUpdateOperationsInput | string | null
    id_token?: NullableStringFieldUpdateOperationsInput | string | null
    session_state?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type SessionUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    sessionToken?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type SessionUncheckedUpdateWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    sessionToken?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type SessionUncheckedUpdateManyWithoutUserInput = {
    id?: StringFieldUpdateOperationsInput | string
    sessionToken?: StringFieldUpdateOperationsInput | string
    expires?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TeamCreateManySportInput = {
    id?: string
    name: string
    slug: string
    abbr?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type GameCreateManySportInput = {
    id?: string
    date: Date | string
    slug: string
    homeTeamId: string
    awayTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type TeamUpdateWithoutSportInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    homeGames?: GameUpdateManyWithoutHomeTeamNestedInput
    awayGames?: GameUpdateManyWithoutAwayTeamNestedInput
    injuries?: InjuryUpdateManyWithoutTeamNestedInput
    profiles?: TeamProfileWeeklyUpdateManyWithoutTeamNestedInput
  }

  export type TeamUncheckedUpdateWithoutSportInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    homeGames?: GameUncheckedUpdateManyWithoutHomeTeamNestedInput
    awayGames?: GameUncheckedUpdateManyWithoutAwayTeamNestedInput
    injuries?: InjuryUncheckedUpdateManyWithoutTeamNestedInput
    profiles?: TeamProfileWeeklyUncheckedUpdateManyWithoutTeamNestedInput
  }

  export type TeamUncheckedUpdateManyWithoutSportInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    slug?: StringFieldUpdateOperationsInput | string
    abbr?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type GameUpdateWithoutSportInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    homeTeam?: TeamUpdateOneRequiredWithoutHomeGamesNestedInput
    awayTeam?: TeamUpdateOneRequiredWithoutAwayGamesNestedInput
    market?: MarketSnapshotUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUpdateOneWithoutGameNestedInput
    writeup?: WriteupUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateWithoutSportInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    homeTeamId?: StringFieldUpdateOperationsInput | string
    awayTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    market?: MarketSnapshotUncheckedUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUncheckedUpdateOneWithoutGameNestedInput
    writeup?: WriteupUncheckedUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateManyWithoutSportInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    homeTeamId?: StringFieldUpdateOperationsInput | string
    awayTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type GameCreateManyHomeTeamInput = {
    id?: string
    sportId: string
    date: Date | string
    slug: string
    awayTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type GameCreateManyAwayTeamInput = {
    id?: string
    sportId: string
    date: Date | string
    slug: string
    homeTeamId: string
    startTime?: Date | string | null
    venue?: string | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type InjuryCreateManyTeamInput = {
    id?: string
    date: Date | string
    player: string
    status: $Enums.InjuryStatus
    note?: string | null
    impact?: $Enums.InjuryImpact | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type TeamProfileWeeklyCreateManyTeamInput = {
    id?: string
    weekStart: Date | string
    summary: string
    tempoRank?: number | null
    offPpp?: number | null
    defPpp?: number | null
    createdAt?: Date | string
    updatedAt?: Date | string
  }

  export type GameUpdateWithoutHomeTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutGamesNestedInput
    awayTeam?: TeamUpdateOneRequiredWithoutAwayGamesNestedInput
    market?: MarketSnapshotUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUpdateOneWithoutGameNestedInput
    writeup?: WriteupUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateWithoutHomeTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    awayTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    market?: MarketSnapshotUncheckedUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUncheckedUpdateOneWithoutGameNestedInput
    writeup?: WriteupUncheckedUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateManyWithoutHomeTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    awayTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type GameUpdateWithoutAwayTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    sport?: SportUpdateOneRequiredWithoutGamesNestedInput
    homeTeam?: TeamUpdateOneRequiredWithoutHomeGamesNestedInput
    market?: MarketSnapshotUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUpdateOneWithoutGameNestedInput
    writeup?: WriteupUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateWithoutAwayTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    homeTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    market?: MarketSnapshotUncheckedUpdateOneWithoutGameNestedInput
    model?: ModelProjectionUncheckedUpdateOneWithoutGameNestedInput
    writeup?: WriteupUncheckedUpdateOneWithoutGameNestedInput
  }

  export type GameUncheckedUpdateManyWithoutAwayTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    sportId?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    slug?: StringFieldUpdateOperationsInput | string
    homeTeamId?: StringFieldUpdateOperationsInput | string
    startTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    venue?: NullableStringFieldUpdateOperationsInput | string | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type InjuryUpdateWithoutTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    player?: StringFieldUpdateOperationsInput | string
    status?: EnumInjuryStatusFieldUpdateOperationsInput | $Enums.InjuryStatus
    note?: NullableStringFieldUpdateOperationsInput | string | null
    impact?: NullableEnumInjuryImpactFieldUpdateOperationsInput | $Enums.InjuryImpact | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type InjuryUncheckedUpdateWithoutTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    player?: StringFieldUpdateOperationsInput | string
    status?: EnumInjuryStatusFieldUpdateOperationsInput | $Enums.InjuryStatus
    note?: NullableStringFieldUpdateOperationsInput | string | null
    impact?: NullableEnumInjuryImpactFieldUpdateOperationsInput | $Enums.InjuryImpact | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type InjuryUncheckedUpdateManyWithoutTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    date?: DateTimeFieldUpdateOperationsInput | Date | string
    player?: StringFieldUpdateOperationsInput | string
    status?: EnumInjuryStatusFieldUpdateOperationsInput | $Enums.InjuryStatus
    note?: NullableStringFieldUpdateOperationsInput | string | null
    impact?: NullableEnumInjuryImpactFieldUpdateOperationsInput | $Enums.InjuryImpact | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TeamProfileWeeklyUpdateWithoutTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    weekStart?: DateTimeFieldUpdateOperationsInput | Date | string
    summary?: StringFieldUpdateOperationsInput | string
    tempoRank?: NullableIntFieldUpdateOperationsInput | number | null
    offPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    defPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TeamProfileWeeklyUncheckedUpdateWithoutTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    weekStart?: DateTimeFieldUpdateOperationsInput | Date | string
    summary?: StringFieldUpdateOperationsInput | string
    tempoRank?: NullableIntFieldUpdateOperationsInput | number | null
    offPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    defPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type TeamProfileWeeklyUncheckedUpdateManyWithoutTeamInput = {
    id?: StringFieldUpdateOperationsInput | string
    weekStart?: DateTimeFieldUpdateOperationsInput | Date | string
    summary?: StringFieldUpdateOperationsInput | string
    tempoRank?: NullableIntFieldUpdateOperationsInput | number | null
    offPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    defPpp?: NullableFloatFieldUpdateOperationsInput | number | null
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    updatedAt?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type BookLineCreateManyMarketInput = {
    id?: string
    book: string
    capturedAt?: Date | string
    spreadHome?: number | null
    spreadAway?: number | null
    total?: number | null
  }

  export type BookLineUpdateWithoutMarketInput = {
    id?: StringFieldUpdateOperationsInput | string
    book?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    spreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    spreadAway?: NullableFloatFieldUpdateOperationsInput | number | null
    total?: NullableFloatFieldUpdateOperationsInput | number | null
  }

  export type BookLineUncheckedUpdateWithoutMarketInput = {
    id?: StringFieldUpdateOperationsInput | string
    book?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    spreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    spreadAway?: NullableFloatFieldUpdateOperationsInput | number | null
    total?: NullableFloatFieldUpdateOperationsInput | number | null
  }

  export type BookLineUncheckedUpdateManyWithoutMarketInput = {
    id?: StringFieldUpdateOperationsInput | string
    book?: StringFieldUpdateOperationsInput | string
    capturedAt?: DateTimeFieldUpdateOperationsInput | Date | string
    spreadHome?: NullableFloatFieldUpdateOperationsInput | number | null
    spreadAway?: NullableFloatFieldUpdateOperationsInput | number | null
    total?: NullableFloatFieldUpdateOperationsInput | number | null
  }



  /**
   * Batch Payload for updateMany & deleteMany & createMany
   */

  export type BatchPayload = {
    count: number
  }

  /**
   * DMMF
   */
  export const dmmf: runtime.BaseDMMF
}